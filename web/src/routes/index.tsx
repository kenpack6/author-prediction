import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/')({
  component: IndexComponent,
})

function IndexComponent() {
  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold text-slate-100">Welcome Home</h1>
      <p className="text-slate-400">
        This is the home page integrated with TanStack Router, React, and Tailwind CSS.
      </p>
    </div>
  )
}
