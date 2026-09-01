import { createRootRoute, Link, Outlet } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/router-devtools'

export const Route = createRootRoute({
  component: RootComponent,
})

function RootComponent() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      <nav className="border-b border-slate-800 bg-slate-950 p-4">
        <div className="max-w-7xl 2xl:max-w-[1600px] mx-auto w-full flex gap-4 text-sm font-semibold">
          <Link
            to="/"
            className="text-slate-400 hover:text-slate-100 [&.active]:text-indigo-400 [&.active]:font-bold"
          >
            Home
          </Link>
          <Link
            to="/about"
            className="text-slate-400 hover:text-slate-100 [&.active]:text-indigo-400 [&.active]:font-bold"
          >
            About
          </Link>
        </div>
      </nav>
      <main className="flex-1 p-6 max-w-7xl 2xl:max-w-[1600px] mx-auto w-full">
        <Outlet />
      </main>
      <TanStackRouterDevtools position="bottom-right" />
    </div>
  )
}
