import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import {
  fetchProjects,
  createProject,
  deleteProject,
  type ProjectResponse,
} from '../lib/api'

export const Route = createFileRoute('/')({
  component: IndexComponent,
})

function IndexComponent() {
  const [projects, setProjects] = useState<ProjectResponse[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [newProjectName, setNewProjectName] = useState<string>('')
  const [creating, setCreating] = useState<boolean>(false)

  const reload = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchProjects()
      setProjects(data)
    } catch (err: unknown) {
      console.error(err)
      setError('Failed to load projects. Please check that the server is running.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let ignore = false
    fetchProjects()
      .then((data) => {
        if (!ignore) {
          setProjects(data)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!ignore) {
          console.error(err)
          setError('Failed to load projects. Please check that the server is running.')
          setLoading(false)
        }
      })

    return () => {
      ignore = true
    }
  }, [])

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newProjectName.trim()) return

    setCreating(true)
    try {
      await createProject({ name: newProjectName.trim() })
      setNewProjectName('')
      await reload()
    } catch (err: unknown) {
      console.error(err)
      alert('Failed to create project')
    } finally {
      setCreating(false)
    }
  }

  const handleDeleteProject = async (id: number, name: string) => {
    if (!confirm(`Are you sure you want to delete project "${name}"?`)) return

    try {
      await deleteProject(id)
      await reload()
    } catch (err: unknown) {
      console.error(err)
      alert('Failed to delete project')
    }
  }

  return (
    <div className="space-y-8">
      {/* Header Section */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight">Projects</h1>
          <p className="text-slate-400 text-sm mt-1">
            Manage your author prediction projects and text sources.
          </p>
        </div>
        <button
          onClick={reload}
          disabled={loading}
          className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 active:bg-slate-900 rounded-lg transition border border-slate-700 disabled:opacity-50"
        >
          {loading ? 'Refreshing...' : 'Refresh List'}
        </button>
      </div>

      {/* New Project Form */}
      <form
        onSubmit={handleCreateProject}
        className="bg-slate-950 p-4 rounded-xl border border-slate-800 flex flex-col sm:flex-row gap-3"
      >
        <input
          type="text"
          placeholder="New Project Name..."
          value={newProjectName}
          onChange={(e) => setNewProjectName(e.target.value)}
          className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
        />
        <button
          type="submit"
          disabled={creating || !newProjectName.trim()}
          className="px-5 py-2 text-sm font-medium bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white rounded-lg transition disabled:opacity-50"
        >
          {creating ? 'Creating...' : 'Create Project'}
        </button>
      </form>

      {/* Content Section */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="animate-pulse bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-3"
            >
              <div className="h-5 bg-slate-800 rounded w-1/2"></div>
              <div className="h-4 bg-slate-800/60 rounded w-1/4"></div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="bg-red-950/40 border border-red-900/50 rounded-xl p-6 text-center space-y-3">
          <p className="text-red-400 font-medium text-sm">{error}</p>
          <button
            onClick={reload}
            className="px-4 py-2 text-xs font-semibold bg-red-900/50 hover:bg-red-800/60 text-red-200 rounded-lg border border-red-800 transition"
          >
            Try Again
          </button>
        </div>
      ) : projects.length === 0 ? (
        <div className="bg-slate-950 border border-dashed border-slate-800 rounded-xl p-12 text-center space-y-2">
          <h3 className="text-lg font-medium text-slate-300">No projects found</h3>
          <p className="text-sm text-slate-500">
            Create your first project above to get started.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {projects.map((project) => (
            <div
              key={project.id}
              className="bg-slate-950 border border-slate-800 hover:border-slate-700 rounded-xl p-5 transition flex flex-col justify-between group shadow-sm"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                    ID: #{project.id}
                  </span>
                  <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-800/60">
                    {project.sources} {project.sources === 1 ? 'source' : 'sources'}
                  </span>
                </div>
                <h3 className="text-xl font-semibold text-slate-100 group-hover:text-indigo-400 transition">
                  {project.name}
                </h3>
              </div>

              <div className="mt-5 pt-3 border-t border-slate-900 flex items-center justify-end">
                <button
                  onClick={() => handleDeleteProject(project.id, project.name)}
                  className="text-xs text-slate-500 hover:text-red-400 transition px-2 py-1 rounded hover:bg-red-950/30"
                >
                  Delete Project
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}


