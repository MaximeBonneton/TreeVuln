import { useState } from 'react';
import { Trees } from 'lucide-react';
import { authApi } from '../api/auth';
import { Alert, Button, Input } from '@/components/ui';

interface LoginProps {
  onLogin: () => void;
}

export function Login({ onLogin }: LoginProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const result = await authApi.login(username, password);
      // Whether status is "authenticated" or "must_change_password",
      // we call onLogin() — App.tsx manages state via checkAuth
      if (result.status === 'authenticated' || result.status === 'must_change_password') {
        onLogin();
      }
    } catch (err: any) {
      setError(err.message || 'Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-md rounded-card border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-6 flex items-center gap-2">
          <Trees size={22} className="text-indigo-600" aria-hidden="true" />
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-slate-900">TreeVuln</h1>
            <p className="text-sm text-slate-500">Sign in to access the application.</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="login-username" className="mb-1 block text-sm font-medium text-slate-700">
              Username
            </label>
            <Input
              id="login-username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Username"
              autoFocus
              required
            />
          </div>
          <div>
            <label htmlFor="login-password" className="mb-1 block text-sm font-medium text-slate-700">
              Password
            </label>
            <Input
              id="login-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              required
            />
          </div>

          {error && <Alert variant="error">{error}</Alert>}

          <Button type="submit" disabled={loading || !username || !password} className="w-full">
            {loading ? 'Signing in...' : 'Sign in'}
          </Button>
        </form>
      </div>
    </div>
  );
}
