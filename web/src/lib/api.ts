import axios, { type AxiosInstance } from 'axios'

export interface ProjectResponse {
  id: number
  name: string
  sources: number
}

export interface ProjectCreate {
  name: string
}

export interface ProjectUpdate {
  name: string
}

export interface SourceListItemResponse {
  id: number
  filename: string
  processed_date: string | null
  project: number
}

export interface SourceResponse {
  id: number
  filename: string
  full_text: string
  processed_date: string | null
  project: number
}

export interface SourceCreate {
  filename: string
  full_text: string
}

export const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Global response interceptor for consistent error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    return Promise.reject(error)
  },
)

export async function fetchProjects(): Promise<ProjectResponse[]> {
  const response = await api.get<ProjectResponse[]>('/projects/')
  return response.data
}

export async function fetchProject(projectId: number): Promise<ProjectResponse> {
  const response = await api.get<ProjectResponse>(`/projects/${projectId}`)
  return response.data
}

export async function createProject(data: ProjectCreate): Promise<ProjectResponse> {
  const response = await api.post<ProjectResponse>('/projects/', data)
  return response.data
}

export async function deleteProject(projectId: number): Promise<void> {
  await api.delete(`/projects/${projectId}`)
}

export async function fetchSources(projectId: number): Promise<SourceListItemResponse[]> {
  const response = await api.get<SourceListItemResponse[]>(`/projects/${projectId}/sources/`)
  return response.data
}

export async function fetchSource(projectId: number, sourceId: number): Promise<SourceResponse> {
  const response = await api.get<SourceResponse>(`/projects/${projectId}/sources/${sourceId}`)
  return response.data
}

export async function createSource(projectId: number, data: SourceCreate): Promise<SourceResponse> {
  const response = await api.post<SourceResponse>(`/projects/${projectId}/sources/`, data)
  return response.data
}

export default api



