import re
from author_prediction.scripts.pipeline_implementation import OnlineAuthorDiarizer

print("test")
path = 'src/author_prediction/data/data_orth.txt'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
print('num_sentences', len(sentences))

dia = OnlineAuthorDiarizer(sim_threshold=0.90, context_window_size=20, min_tokens_for_update=15)
results = dia.process_document(sentences[::])
for i, r in enumerate(results):
    print(f"Iteration {i}:")
    print(r['sentence_idx'], r['author'], round(r['similarity_to_matched'], 4), r['author_changed'])