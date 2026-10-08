import { create } from 'zustand';

export type UserRole = 'ADMIN' | 'OPERATOR' | 'VIEWER';

export interface UserProfile {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  fullName: string;
}

interface AuthState {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  login: (token: string, user: UserProfile) => void;
  logout: () => void;
  quickSwitchRole: (role: UserRole) => void;
  hasRole: (roles: UserRole[]) => boolean;
}

const DEFAULT_DEMO_USERS: Record<UserRole, UserProfile> = {
  ADMIN: {
    id: 'user-admin-001',
    username: 'admin',
    email: 'admin@crowdsight.ai',
    role: 'ADMIN',
    fullName: 'Quản Trị Viên (Admin)',
  },
  OPERATOR: {
    id: 'user-operator-001',
    username: 'operator',
    email: 'operator@crowdsight.ai',
    role: 'OPERATOR',
    fullName: 'Giám Sát Viên (Operator)',
  },
  VIEWER: {
    id: 'user-viewer-001',
    username: 'viewer',
    email: 'viewer@crowdsight.ai',
    role: 'VIEWER',
    fullName: 'Khách Xem (Viewer)',
  },
};

const STORAGE_KEY_TOKEN = 'crowdsight_jwt_token';
const STORAGE_KEY_USER = 'crowdsight_auth_user';

const getInitialState = (): { token: string | null; user: UserProfile | null } => {
  if (typeof window === 'undefined') {
    return { token: null, user: DEFAULT_DEMO_USERS.OPERATOR };
  }
  try {
    const savedToken = localStorage.getItem(STORAGE_KEY_TOKEN);
    const savedUserJson = localStorage.getItem(STORAGE_KEY_USER);
    if (savedToken && savedUserJson) {
      const parsedUser = JSON.parse(savedUserJson) as UserProfile;
      return { token: savedToken, user: parsedUser };
    }
  } catch {
    // ignore
  }
  // Default to Operator for seamless demo experience
  return { token: 'mock-demo-token-operator', user: DEFAULT_DEMO_USERS.OPERATOR };
};

const initial = getInitialState();

export const useAuthStore = create<AuthState>((set, get) => ({
  user: initial.user,
  token: initial.token,
  isAuthenticated: Boolean(initial.user),
  isLoading: false,

  login: (token, user) => {
    try {
      localStorage.setItem(STORAGE_KEY_TOKEN, token);
      localStorage.setItem(STORAGE_KEY_USER, JSON.stringify(user));
    } catch {}
    set({ token, user, isAuthenticated: true });
  },

  logout: () => {
    try {
      localStorage.removeItem(STORAGE_KEY_TOKEN);
      localStorage.removeItem(STORAGE_KEY_USER);
    } catch {}
    set({ token: null, user: null, isAuthenticated: false });
  },

  quickSwitchRole: (role) => {
    const targetUser = DEFAULT_DEMO_USERS[role];
    const mockToken = `mock-demo-token-${role.toLowerCase()}`;
    try {
      localStorage.setItem(STORAGE_KEY_TOKEN, mockToken);
      localStorage.setItem(STORAGE_KEY_USER, JSON.stringify(targetUser));
    } catch {}
    set({ token: mockToken, user: targetUser, isAuthenticated: true });
  },

  hasRole: (roles) => {
    const current = get().user;
    if (!current) return false;
    return roles.includes(current.role);
  },
}));
