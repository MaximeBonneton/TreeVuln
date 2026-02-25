import { useEffect, useState } from 'react'
import { TreeBuilder } from './components/TreeBuilder'
import { Login } from './components/Login'

function App() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null)

  useEffect(() => {
    fetch('/api/v1/auth/check', { credentials: 'same-origin' })
      .then(res => res.json())
      .then(data => setAuthenticated(data.authenticated))
      .catch(() => setAuthenticated(false))
  }, [])

  if (authenticated === null) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900">
        <div className="text-gray-400">Chargement...</div>
      </div>
    )
  }

  if (!authenticated) {
    return <Login onLogin={() => setAuthenticated(true)} />
  }

  return <TreeBuilder />
}

export default App
