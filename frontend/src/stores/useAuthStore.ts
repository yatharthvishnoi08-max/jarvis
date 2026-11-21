import { create } from 'zustand';

interface AuthState {
  token: string;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  setToken: (token: string) => void;
  logout: () => void;
  checkAuth: () => Promise<boolean>;
}

const getInitialToken = () => {
  if (typeof window !== 'undefined') {
    const urlParam = new URLSearchParams(window.location.hash.slice(1)).get('token')
      || new URLSearchParams(window.location.search).get('token');
    if (urlParam) {
      localStorage.setItem('jarvis_auth_token', urlParam.trim());
      window.history.replaceState({}, document.title, window.location.pathname);
      return urlParam.trim();
    }
  }
  return typeof localStorage !== 'undefined' ? localStorage.getItem('jarvis_auth_token') || '' : '';
};

export const useAuthStore = create<AuthState>((set, get) => ({
  token: getInitialToken(),
  isAuthenticated: false,
  isLoading: true,
  error: null,

  setToken: (token: string) => {
    localStorage.setItem('jarvis_auth_token', token.trim());
    set({ token: token.trim(), error: null });
    get().checkAuth();
  },

  logout: () => {
    localStorage.removeItem('jarvis_auth_token');
    set({ token: '', isAuthenticated: false });
  },

  checkAuth: async () => {
    let token = get().token;

    // 1. Check if backend requires authentication (seamless local mode)
    try {
      const statusRes = await fetch('/api/auth/status');
      if (statusRes.ok) {
        const data = await statusRes.json();
        if (!data.auth_required && (data.is_local ?? true)) {
          const autoToken = token || 'local-owner';
          localStorage.setItem('jarvis_auth_token', autoToken);
          set({ token: autoToken, isAuthenticated: true, isLoading: false, error: null });
          return true;
        }
      }
    } catch {
      // Backend status unreachable; fall back to local token verification
    }

    if (!token) {
      set({ isAuthenticated: false, isLoading: false });
      return false;
    }

    // 2. If auth is required, verify token
    try {
      const res = await fetch('/api/auth/verify', {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        set({ isAuthenticated: true, isLoading: false, error: null });
        return true;
      } else {
        set({ isAuthenticated: false, isLoading: false, error: 'Invalid or expired token.' });
        return false;
      }
    } catch {
      set({ isAuthenticated: false, isLoading: false, error: 'Cannot reach JARVIS server.' });
      return false;
    }
  }
}));
