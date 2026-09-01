import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  fetchProjects,
  createProject,
  deleteProject,
} from '../lib/api'

export const Route = createFileRoute('/')({
  component: IndexComponent,
})

function IndexComponent() {
  const queryClient = useQueryClient()
  const [newProjectName, setNewProjectName] = useState<string>('')

  // Query projects list
  const {
    data: projects = [],
    isLoading,
    isFetching,
    error,
    refetch,
  } = useQuery({
    queryKey: ['projects'],
    queryFn: fetchProjects,
  })

  // Mutation to create a project
  const createMutation = useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      setNewProjectName('')
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
    onError: (err) => {
      console.error(err)
      alert('Failed to create project')
    },
  })

  // Mutation to delete a project
  const deleteMutation = useMutation({
    mutationFn: deleteProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
    onError: (err) => {
      console.error(err)
      alert('Failed to delete project')
    },
  })

  const handleCreateProject = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newProjectName.trim()) return
    createMutation.mutate({ name: newProjectName.trim() })
  }

  const handleDeleteProject = (id: number, name: string) => {
    if (!confirm(`Are you sure you want to delete project "${name}"?`)) return
    deleteMutation.mutate(id)
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
          onClick={() => refetch()}
          disabled={isFetching}
          className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 active:bg-slate-900 rounded-lg transition border border-slate-700 disabled:opacity-50"
        >
          {isFetching ? 'Refreshing...' : 'Refresh List'}
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
          disabled={createMutation.isPending || !newProjectName.trim()}
          className="px-5 py-2 text-sm font-medium bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white rounded-lg transition disabled:opacity-50"
        >
          {createMutation.isPending ? 'Creating...' : 'Create Project'}
        </button>
      </form>

      {/* Content Section */}
      {isLoading ? (
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
          <p className="text-red-400 font-medium text-sm">
            Failed to load projects. Please check that the server is running.
          </p>
          <button
            onClick={() => refetch()}
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
              <Link
                to="/projects/$projectId"
                params={{ projectId: project.id.toString() }}
                className="space-y-2 block"
              >
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
              </Link>

              <div className="mt-5 pt-3 border-t border-slate-900 flex items-center justify-between">
                <Link
                  to="/projects/$projectId"
                  params={{ projectId: project.id.toString() }}
                  className="text-xs font-medium text-indigo-400 hover:text-indigo-300"
                >
                  View Sources →
                </Link>
                <button
                  onClick={() => handleDeleteProject(project.id, project.name)}
                  disabled={deleteMutation.isPending}
                  className="text-xs text-slate-500 hover:text-red-400 transition px-2 py-1 rounded hover:bg-red-950/30 disabled:opacity-50"
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



