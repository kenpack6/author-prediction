import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  fetchProject,
  fetchSources,
  fetchSource,
  fetchAuthors,
  createSource,
  type SourceCreate,
} from '../lib/api'

export const Route = createFileRoute('/projects/$projectId')({
  component: ProjectDetailComponent,
})

function ProjectDetailComponent() {
  const queryClient = useQueryClient()
  const { projectId } = Route.useParams()
  const pId = parseInt(projectId, 10)

  const [selectedSourceId, setSelectedSourceId] = useState<number | null>(null)

  // Add Source modal/form state
  const [showAddModal, setShowAddModal] = useState<boolean>(false)
  const [newFilename, setNewFilename] = useState<string>('')
  const [newFullText, setNewFullText] = useState<string>('')

  // Query project details
  const {
    data: project,
    isLoading: loadingProject,
    error: projectError,
  } = useQuery({
    queryKey: ['projects', pId],
    queryFn: () => fetchProject(pId),
    enabled: !isNaN(pId),
  })

  // Query sources list
  const {
    data: sources = [],
    isLoading: loadingSources,
  } = useQuery({
    queryKey: ['sources', pId],
    queryFn: () => fetchSources(pId),
    enabled: !isNaN(pId),
  })

  // Query authors list
  const {
    data: authors = [],
    isLoading: loadingAuthors,
  } = useQuery({
    queryKey: ['authors', pId],
    queryFn: () => fetchAuthors(pId),
    enabled: !isNaN(pId),
  })

  // Query selected source detail
  const {
    data: selectedSource,
    isLoading: loadingSourceDetail,
  } = useQuery({
    queryKey: ['source', pId, selectedSourceId],
    queryFn: () => fetchSource(pId, selectedSourceId!),
    enabled: !isNaN(pId) && selectedSourceId !== null,
  })

  // Mutation to create a source
  const createSourceMutation = useMutation({
    mutationFn: (data: SourceCreate) => createSource(pId, data),
    onSuccess: (created) => {
      setNewFilename('')
      setNewFullText('')
      setShowAddModal(false)
      queryClient.invalidateQueries({ queryKey: ['sources', pId] })
      queryClient.invalidateQueries({ queryKey: ['projects', pId] })
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      queryClient.invalidateQueries({ queryKey: ['authors', pId] })
      setSelectedSourceId(created.id)
    },
    onError: (err: any) => {
      console.error(err)
      const detail = err?.response?.data?.detail
      alert(detail || 'Failed to create source')
    },
  })

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setNewFilename(file.name)
    try {
      const text = await file.text()
      setNewFullText(text)
    } catch (err) {
      console.error('Error reading file:', err)
      alert('Failed to read file content')
    }
  }

  const handleCreateSource = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newFilename.trim() || !newFullText.trim()) return
    createSourceMutation.mutate({
      filename: newFilename.trim(),
      full_text: newFullText,
    })
  }

  if (loadingProject) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-6 bg-slate-800 rounded w-1/4"></div>
        <div className="h-10 bg-slate-800 rounded w-1/2"></div>
        <div className="h-64 bg-slate-950 rounded border border-slate-800"></div>
      </div>
    )
  }

  if (projectError || !project) {
    return (
      <div className="space-y-4">
        <Link to="/" className="text-xs text-indigo-400 hover:underline">
          ← Back to Projects
        </Link>
        <div className="bg-red-950/40 border border-red-900/50 rounded-xl p-6 text-red-300">
          Failed to load project details. Please check that the server is running.
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div className="space-y-1">
          <Link
            to="/"
            className="text-xs font-semibold text-slate-400 hover:text-slate-200 transition inline-flex items-center gap-1"
          >
            ← Back to Projects
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-100">{project.name}</h1>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
              ID: #{project.id}
            </span>
          </div>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="px-4 py-2 text-sm font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition"
        >
          + Add Source
        </button>
      </div>

      {/* Main Three-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Sidebar: Sources List (3 cols) */}
        <div className="lg:col-span-3 bg-slate-950 border border-slate-800 rounded-xl overflow-hidden flex flex-col min-h-[500px]">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
            <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
              Sources ({sources.length})
            </h2>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-slate-800/60 max-h-[600px]">
            {loadingSources ? (
              <div className="p-4 space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="animate-pulse h-10 bg-slate-900 rounded"></div>
                ))}
              </div>
            ) : sources.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-xs">
                No sources added yet. Click "+ Add Source" above.
              </div>
            ) : (
              sources.map((src) => {
                const isSelected = selectedSourceId === src.id
                return (
                  <div
                    key={src.id}
                    onClick={() => setSelectedSourceId(src.id)}
                    className={`p-3.5 flex items-center justify-between cursor-pointer transition text-sm ${
                      isSelected
                        ? 'bg-indigo-950/60 border-l-4 border-indigo-500 text-slate-100 font-medium'
                        : 'hover:bg-slate-900/60 text-slate-300'
                    }`}
                  >
                    <div className="truncate pr-2">
                      <div className="truncate font-mono text-xs text-slate-200">{src.filename}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        {src.processed_date
                          ? new Date(src.processed_date).toLocaleDateString()
                          : 'Unprocessed'}
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>

        {/* Center Panel: Source Detail / Viewer (6 cols) */}
        <div className="lg:col-span-6 bg-slate-950 border border-slate-800 rounded-xl overflow-hidden min-h-[500px] flex flex-col">
          {loadingSourceDetail ? (
            <div className="p-8 space-y-4 animate-pulse">
              <div className="h-6 bg-slate-800 rounded w-1/3"></div>
              <div className="h-4 bg-slate-800 rounded w-1/4"></div>
              <div className="h-64 bg-slate-900 rounded mt-4"></div>
            </div>
          ) : selectedSource ? (
            <div className="flex flex-col h-full">
              {/* Viewer Header */}
              <div className="p-4 border-b border-slate-800 bg-slate-900/40 flex flex-col gap-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h3 className="text-lg font-bold text-slate-100 font-mono">
                      {selectedSource.filename}
                    </h3>
                    <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
                      <span>Source ID: #{selectedSource.id}</span>
                      <span>•</span>
                      <span>
                        Status:{' '}
                        {selectedSource.processed_date
                          ? `Processed on ${new Date(selectedSource.processed_date).toLocaleString()}`
                          : 'Unprocessed'}
                      </span>
                    </div>
                  </div>
                  <div className="text-xs text-slate-400 bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800 font-mono">
                    {selectedSource.full_text.split(/\s+/).filter(Boolean).length} words |{' '}
                    {selectedSource.full_text.length} chars
                  </div>
                </div>

                {/* Associated Authors for Source */}
                <div className="pt-2 border-t border-slate-800/60 flex flex-wrap items-center gap-2">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Associated Authors:
                  </span>
                  {selectedSource.authors && selectedSource.authors.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {selectedSource.authors.map((authorId) => (
                        <span
                          key={authorId}
                          className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium bg-indigo-950 text-indigo-300 border border-indigo-800/60"
                        >
                          Author #{authorId}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-xs text-slate-500 italic">
                      {selectedSource.processed_date
                        ? 'No authors associated with this source'
                        : 'Unprocessed (authors will appear after inference)'}
                    </span>
                  )}
                </div>
              </div>

              {/* Viewer Content Textbox */}
              <div className="flex-1 p-5 overflow-auto bg-slate-950">
                <pre className="font-mono text-sm text-slate-200 whitespace-pre-wrap break-words leading-relaxed select-text bg-slate-900/50 p-4 rounded-lg border border-slate-800/80">
                  {selectedSource.full_text}
                </pre>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-12 text-center text-slate-500">
              <div className="w-12 h-12 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-400 text-xl mb-3">
                📄
              </div>
              <h4 className="text-base font-medium text-slate-300">No Source Selected</h4>
              <p className="text-xs text-slate-500 max-w-sm mt-1">
                Select a source file from the sidebar to inspect its text content and associated authors.
              </p>
            </div>
          )}
        </div>

        {/* Right Sidebar: Authors List (3 cols) */}
        <div className="lg:col-span-3 bg-slate-950 border border-slate-800 rounded-xl overflow-hidden flex flex-col min-h-[500px]">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
            <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
              Authors ({authors.length})
            </h2>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-slate-800/60 max-h-[600px]">
            {loadingAuthors ? (
              <div className="p-4 space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="animate-pulse h-10 bg-slate-900 rounded"></div>
                ))}
              </div>
            ) : authors.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-xs">
                No authors detected yet. Authors will appear here once sources are processed.
              </div>
            ) : (
              authors.map((author) => {
                const isAssociatedWithSelected = selectedSource?.authors?.includes(author.id)
                return (
                  <div
                    key={author.id}
                    className={`p-3.5 flex items-center justify-between transition text-sm ${
                      isAssociatedWithSelected
                        ? 'bg-indigo-950/50 border-l-4 border-indigo-500 text-slate-100 font-medium'
                        : 'hover:bg-slate-900/60 text-slate-300'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-slate-200">
                        Author #{author.id}
                      </span>
                    </div>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
                      {author.sources} {author.sources === 1 ? 'source' : 'sources'}
                    </span>
                  </div>
                )
              })
            )}
          </div>
        </div>
      </div>

      {/* Add Source Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-slate-100">Add New Source</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-slate-400 hover:text-slate-200 text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateSource} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Select Plain-Text File
                </label>
                <input
                  type="file"
                  accept=".txt,.md,.json,.csv,.text,text/plain"
                  onChange={handleFileSelect}
                  className="w-full text-xs text-slate-400 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-slate-800 file:text-indigo-300 hover:file:bg-slate-700 cursor-pointer bg-slate-950 border border-slate-700 rounded-lg p-1"
                />
              </div>

              <div className="relative border-t border-slate-800 my-2 text-center">
                <span className="bg-slate-900 px-2 text-[10px] uppercase text-slate-500 font-bold relative -top-2.5">
                  Or enter details manually
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Filename
                </label>
                <input
                  type="text"
                  placeholder="e.g. essay_chapter_1.txt"
                  value={newFilename}
                  onChange={(e) => setNewFilename(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Full Text Content
                </label>
                <textarea
                  rows={6}
                  placeholder="Paste source text here..."
                  value={newFullText}
                  onChange={(e) => setNewFullText(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createSourceMutation.isPending}
                  className="px-4 py-2 text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition disabled:opacity-50"
                >
                  {createSourceMutation.isPending ? 'Saving...' : 'Add Source'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
