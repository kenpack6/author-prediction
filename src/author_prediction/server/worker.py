import asyncio
import multiprocessing as mp
import traceback
from dataclasses import dataclass

import asyncpg
from pgvector.asyncpg import register_vector

from author_prediction.deep_stylometry_encoder import DeepStylometryEncoder
from author_prediction.pipeline_implementation import run_pipeline
from author_prediction.profile_tracker import AuthorProfile, AuthorProfileTracker

MAX_CHARS = 100000
MAX_SENTENCES = None

context_window_size = 20
stride = 5
sim_threshold = 0.94
ema_alpha = 0.22
min_tokens_for_update = 15
merge_threshold = 0.95

SENTINEL = None

@dataclass
class InferenceJob:
    project_id: int
    source_id: int

class InferenceWorker(mp.Process):
    def __init__(self, database_url: str):
        mp.Process.__init__(self)

        self.job_queue = mp.Queue()
        self.result_queue = mp.Queue()
        self.database_url = database_url
        self.db_pool: asyncpg.Pool = None
        self.encoder: DeepStylometryEncoder = None

    def run(self):
        asyncio.get_event_loop().run_until_complete(self._run())

    async def _run(self):
        self.encoder = DeepStylometryEncoder()
        self.db_pool = await asyncpg.create_pool(self.database_url, init=lambda conn: register_vector(conn))

        await self.queue_unprocessed()

        while True:
            job = self.job_queue.get()
            if job is SENTINEL:
                break
            try:
                result = await self.run_inference(job)
                self.result_queue.put(result)
            except Exception as e:
                traceback.print_exc()
                self.result_queue.put(e)

    async def queue_unprocessed(self):
        async with self.db_pool.acquire() as conn:
            unprocessed_sources = await conn.fetch("""
            SELECT id, project FROM sources
                WHERE processed_date IS NULL""")
            for source in unprocessed_sources:
                self.put(source[0], source[1])

    async def load_job(self, job: InferenceJob):
        async with self.db_pool.acquire() as conn:
            authors_raw = await conn.fetch("""
                SELECT id, centroid FROM authors
                WHERE project = $1
                """, job.project_id)
            source_text = await conn.fetchval("""
                SELECT full_text FROM sources
                WHERE id = $1 AND project = $2""", job.source_id, job.project_id)
        authors = {f"db_{author['id']}" : AuthorProfile(f"db_{author['id']}",
                                    author["centroid"].to_numpy(),
                                    sample_count=0) for author in authors_raw}
        return authors, source_text

    async def run_inference(self, job: InferenceJob):
        authors, source_text = await self.load_job(job)
        print("Loaded job ", job.source_id)
        tracker = AuthorProfileTracker(
            sim_threshold=sim_threshold,
            ema_alpha=ema_alpha,
            min_tokens_for_update=min_tokens_for_update,
        )
        tracker.profiles = authors
        print("Loaded tracker ", job.source_id)

        result = run_pipeline(
            source_text,
            encoder=self.encoder,
            tracker=tracker,
            context_window_size=context_window_size,
            stride=stride,
            merge_threshold=merge_threshold,
        )
        print("Inference done for job ", job.source_id)
        async with self.db_pool.acquire() as conn, conn.transaction():
            new_profiles = {}
            for profile_id in tracker.profiles:
                location, num = profile_id.split('_')
                profile = tracker.profiles[profile_id]
                if location == 'db':
                    await conn.execute("""
                    UPDATE authors
                    SET centroid = $1
                        WHERE id = $2
                            AND project = $3""",
                    profile.centroid, int(num), job.project_id)
                else:
                    new_id = await conn.fetchval("""
                    INSERT INTO authors (centroid, project)
                        VALUES ($1, $2)
                            RETURNING id""",
                    profile.centroid, job.project_id)
                    new_profiles[profile_id] = new_id

            for event in result['merge_events']:
                location, num = event['merged_from'][0].split('_')
                if location == 'db':
                    location_new, num_new = event['kept'].split('_')
                    if location_new == 'db':
                        dest_id = int(num_new)
                    else:
                        dest_id = new_profiles[event['kept']]
                    await conn.execute("""
                    UPDATE source_authors
                    SET author = $1
                        WHERE source = $2""",
                                       dest_id, job.source_id)

                    await conn.execute("""
                    DELETE FROM authors
                    WHERE id = $1 AND project = $2""",
                                       int(num), job.project_id)

            associated_authors = [(*profile['author_id'].split('_'), profile['author_id']) for profile in result['assignments']]
            associated_authors_ids = [int(num) if loc == 'db' else author_id for loc, num, author_id in associated_authors]
            await conn.executemany("""
            INSERT INTO source_authors (source, author)
                VALUES ($1, $2)
                    ON CONFLICT DO NOTHING""",
                                   [(job.source_id, a) for a in associated_authors_ids])

            await conn.execute("""
            UPDATE sources
            SET processed_date = NOW()
                WHERE id = $1 AND project = $2""",
            job.source_id, job.project_id)

    def shutdown(self):
        self.job_queue.put(SENTINEL)

    def put(self, source_id: int, project_id: int):
        job = InferenceJob(source_id=source_id, project_id=project_id)
        self.job_queue.put(job)
