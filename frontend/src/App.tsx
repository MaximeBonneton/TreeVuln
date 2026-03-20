import { useState, useEffect } from 'react';
import { TreeBuilder } from './components/TreeBuilder';
import { Login } from './components/Login';
import SetupScreen from './components/SetupScreen';
import ChangePasswordDialog from './components/ChangePasswordDialog';
import { authApi, AuthStatus } from './api/auth';
import { useTreeStore } from './stores/treeStore';
import { useEnterpriseStore } from './enterprise/enterpriseStore';

type AppState = 'loading' | 'setup_required' | 'unauthenticated' | 'must_change_password' | 'authenticated';

function App() {
  const [state, setState] = useState<AppState>('loading');
  const setCurrentUser = useTreeStore(s => s.setCurrentUser);

  const checkAuth = async () => {
    try {
      // Charger le statut de licence (Community/Enterprise)
      useEnterpriseStore.getState().loadLicense().catch(() => {});

      const result: AuthStatus = await authApi.check();
      setState(result.status as AppState);
      if (result.status === 'authenticated' && result.user) {
        setCurrentUser(result.user);
      } else if (result.status === 'must_change_password' && result.user) {
        setCurrentUser(result.user);
      } else {
        setCurrentUser(null);
      }
    } catch {
      setState('unauthenticated');
      setCurrentUser(null);
    }
  };

  useEffect(() => { checkAuth(); }, []);

  if (state === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="text-gray-400">Chargement...</div>
      </div>
    );
  }

  if (state === 'setup_required') {
    return <SetupScreen onComplete={checkAuth} />;
  }

  if (state === 'unauthenticated') {
    return <Login onLogin={checkAuth} />;
  }

  if (state === 'must_change_password') {
    return <ChangePasswordDialog forced onComplete={checkAuth} />;
  }

  return <TreeBuilder />;
}

export default App;
