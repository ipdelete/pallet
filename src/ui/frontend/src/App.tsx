import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import './App.css'

interface RepositoryListResponse {
  repositories: string[]
}

function App() {
  const [repositories, setRepositories] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchRepositories()
  }, [])

  const fetchRepositories = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await fetch('http://localhost:8080/api/repositories')

      if (!response.ok) {
        throw new Error(`Failed to fetch repositories: ${response.statusText}`)
      }

      const data: RepositoryListResponse = await response.json()
      setRepositories(data.repositories)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="container mx-auto max-w-4xl">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Registry Repositories</h1>
          <p className="text-muted-foreground">
            Browse OCI registry repositories
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Available Repositories</CardTitle>
            <CardDescription>
              List of all repositories in the OCI registry
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading && (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            )}

            {error && (
              <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md">
                <p className="font-semibold">Error</p>
                <p className="text-sm">{error}</p>
              </div>
            )}

            {!loading && !error && repositories.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                No repositories found
              </div>
            )}

            {!loading && !error && repositories.length > 0 && (
              <div className="space-y-2">
                {repositories.map((repo) => (
                  <div
                    key={repo}
                    className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 bg-primary rounded-full"></div>
                      <span className="font-mono text-sm">{repo}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="mt-4 flex justify-end">
          <button
            onClick={fetchRepositories}
            disabled={loading}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default App
