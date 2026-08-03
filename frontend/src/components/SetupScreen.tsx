import { useState, FormEvent } from 'react';
import { Trees } from 'lucide-react';
import { authApi } from '../api/auth';
import { Alert, Button, Input } from '@/components/ui';

interface SetupScreenProps {
  onComplete: () => void;
}

export default function SetupScreen({ onComplete }: SetupScreenProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');

    if (password.length < 12) {
      setError('Password must be at least 12 characters');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      await authApi.setup(username, password);
      onComplete();
    } catch (err: any) {
      setError(err.message || 'Setup error');
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
            <p className="text-sm text-slate-500">
              Initial setup — Create the administrator account
            </p>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="setup-username" className="mb-1 block text-sm font-medium text-slate-700">
              Username
            </label>
            <Input
              id="setup-username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="admin"
              required
              autoFocus
            />
          </div>
          <div>
            <label htmlFor="setup-password" className="mb-1 block text-sm font-medium text-slate-700">
              Password
            </label>
            <Input
              id="setup-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="12 characters minimum"
              required
            />
          </div>
          <div>
            <label htmlFor="setup-confirm" className="mb-1 block text-sm font-medium text-slate-700">
              Confirm password
            </label>
            <Input
              id="setup-confirm"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>
          {error && <Alert variant="error">{error}</Alert>}
          <Button type="submit" disabled={loading} className="w-full">
            {loading ? 'Creating...' : 'Create administrator account'}
          </Button>
        </form>
      </div>
    </div>
  );
}
