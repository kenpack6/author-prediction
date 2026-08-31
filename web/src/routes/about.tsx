import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/about')({
  component: AboutComponent,
})

function AboutComponent() {
  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold text-slate-100">About</h1>
      <p className="text-slate-400">
        Author Prediction web interface built with React, TypeScript, Vite, Tailwind CSS, and TanStack Router.
      </p>
    </div>
  )
}
