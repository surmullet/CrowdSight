import React, { useState, useRef, useEffect } from 'react';
import {
  Shield,
  ShieldAlert,
  User,
  LogOut,
  ChevronDown,
  KeyRound,
  Check,
  Eye,
  Lock,
} from 'lucide-react';
import { useAuthStore, type UserRole } from '@/shared/state/authStore';

export const UserNavBadge: React.FC = () => {
  const { user, quickSwitchRole, login, logout } = useAuthStore();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [usernameInput, setUsernameInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleRealLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError(null);
    setIsLoading(true);
    try {
      const resp = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: usernameInput, password: passwordInput }),
      });
      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || 'Đăng nhập không thành công');
      }
      const data = await resp.json();
      login(data.access_token, {
        id: data.user.id,
        username: data.user.username,
        email: data.user.email,
        role: data.user.role as UserRole,
        fullName: data.user.full_name || data.user.username,
      });
      setShowLoginModal(false);
      setUsernameInput('');
      setPasswordInput('');
    } catch (err: any) {
      setLoginError(err.message || 'Lỗi kết nối máy chủ');
    } finally {
      setIsLoading(false);
    }
  };

  const roleCardConfig: Record<
    UserRole,
    {
      title: string;
      label: string;
      desc: string;
      badgeCls: string;
      activeBorderCls: string;
      activeBgCls: string;
      icon: React.ReactNode;
    }
  > = {
    ADMIN: {
      title: 'Quản Trị Viên (Admin)',
      label: 'QUẢN TRỊ VIÊN',
      desc: 'Toàn quyền quản trị, xóa phiên & cascade artifact',
      badgeCls: 'bg-red-500/15 text-red-400 border-red-500/30',
      activeBorderCls: 'border-red-500/50',
      activeBgCls: 'bg-red-500/10',
      icon: <ShieldAlert className="w-4 h-4 text-red-400 shrink-0" />,
    },
    OPERATOR: {
      title: 'Giám Sát Viên (Operator)',
      label: 'GIÁM SÁT VIÊN',
      desc: 'Vận hành: tạo phiên, chỉnh vùng & ghi chú hiện trường',
      badgeCls: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
      activeBorderCls: 'border-cyan-500/50',
      activeBgCls: 'bg-cyan-500/10',
      icon: <Shield className="w-4 h-4 text-cyan-400 shrink-0" />,
    },
    VIEWER: {
      title: 'Khách Xem (Viewer)',
      label: 'KHÁCH XEM',
      desc: 'Chế độ chỉ đọc: xem kết quả, khóa tạo phiên & chỉnh sửa',
      badgeCls: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
      activeBorderCls: 'border-slate-400/50',
      activeBgCls: 'bg-slate-500/10',
      icon: <Eye className="w-4 h-4 text-slate-300 shrink-0" />,
    },
  };

  const currentRole = user?.role || 'OPERATOR';
  const currentCfg = roleCardConfig[currentRole];

  return (
    <div className="relative select-none" ref={dropdownRef}>
      {/* 1. Header Trigger Pill */}
      <button
        type="button"
        onClick={() => setDropdownOpen(!dropdownOpen)}
        style={{ backgroundColor: '#141B26' }}
        className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg border border-[#253347] hover:border-brand-gold/50 transition-all cursor-pointer text-left shadow-sm group"
        title="Quản lý tài khoản & Phân quyền RBAC"
      >
        <div className="w-6 h-6 rounded-full bg-[#1C2638] flex items-center justify-center border border-[#2C3B52] text-brand-gold">
          <User className="w-3.5 h-3.5" />
        </div>
        <div className="flex flex-col">
          <span className="text-xs font-semibold text-brand-text-primary leading-tight group-hover:text-brand-gold transition-colors">
            {user?.fullName || user?.username || 'Khách'}
          </span>
          <span
            className={`text-[9px] font-mono uppercase font-bold tracking-wider px-1 py-0.2 rounded border w-fit mt-0.5 ${currentCfg.badgeCls}`}
          >
            {currentCfg.label}
          </span>
        </div>
        <ChevronDown
          className={`w-3.5 h-3.5 text-brand-text-muted ml-0.5 transition-transform duration-200 ${
            dropdownOpen ? 'rotate-180 text-brand-gold' : ''
          }`}
        />
      </button>

      {/* 2. Dropdown Popover (Solid Dark Container) */}
      {dropdownOpen && (
        <div
          style={{ backgroundColor: '#131B2A' }}
          className="absolute right-0 mt-2 w-80 rounded-2xl border border-[#2B394E] shadow-2xl z-50 text-xs overflow-hidden"
        >
          {/* Top user profile banner */}
          <div style={{ backgroundColor: '#182234' }} className="p-3.5 border-b border-[#243144]">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-[#202D42] border border-[#30425C] flex items-center justify-center text-brand-gold font-bold text-xs">
                {user?.fullName?.charAt(0) || 'U'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-brand-text-primary truncate">
                  {user?.fullName || 'Người dùng'}
                </p>
                <p className="text-[11px] text-brand-text-muted truncate">
                  {user?.email || 'user@crowdsight.ai'}
                </p>
              </div>
              <span
                className={`text-[9px] font-mono uppercase font-bold px-1.5 py-0.5 rounded border shrink-0 ${currentCfg.badgeCls}`}
              >
                {currentCfg.label}
              </span>
            </div>
          </div>

          {/* Quick role switcher cards */}
          <div className="p-3 space-y-2">
            <div className="flex items-center justify-between px-1">
              <span className="text-[10px] font-mono uppercase font-bold text-brand-text-muted tracking-wider">
                Chuyển vai trò thử nghiệm:
              </span>
              <span className="text-[10px] text-brand-gold font-mono">RBAC DEMO</span>
            </div>

            <div className="space-y-1.5">
              {(['ADMIN', 'OPERATOR', 'VIEWER'] as UserRole[]).map((r) => {
                const isSelected = r === currentRole;
                const cfg = roleCardConfig[r];
                return (
                  <button
                    key={r}
                    type="button"
                    onClick={() => {
                      quickSwitchRole(r);
                      setDropdownOpen(false);
                    }}
                    style={{ backgroundColor: isSelected ? undefined : '#172030' }}
                    className={`w-full text-left p-2.5 rounded-xl border transition-all cursor-pointer flex items-start gap-2.5 ${
                      isSelected
                        ? `${cfg.activeBorderCls} ${cfg.activeBgCls} shadow-sm`
                        : 'border-[#223043] hover:border-[#2F415A] hover:bg-[#1B263A]'
                    }`}
                  >
                    <div className="mt-0.5">{cfg.icon}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1">
                        <span
                          className={`font-semibold text-xs ${
                            isSelected ? 'text-brand-text-primary font-bold' : 'text-brand-text-primary/90'
                          }`}
                        >
                          {cfg.title}
                        </span>
                        {isSelected && (
                          <div className="w-4 h-4 rounded-full bg-brand-gold/20 flex items-center justify-center text-brand-gold shrink-0">
                            <Check className="w-2.5 h-2.5" />
                          </div>
                        )}
                      </div>
                      <p className="text-[10px] text-brand-text-muted leading-tight mt-0.5">
                        {cfg.desc}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Footer Actions */}
          <div style={{ backgroundColor: '#101724' }} className="p-2 border-t border-[#202C3E] space-y-1">
            <button
              type="button"
              onClick={() => {
                setDropdownOpen(false);
                setShowLoginModal(true);
              }}
              className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-left text-brand-text-muted hover:text-brand-text-primary hover:bg-[#182335] transition-colors cursor-pointer"
            >
              <KeyRound className="w-3.5 h-3.5 text-brand-gold" />
              <span>Đăng nhập tài khoản thật</span>
            </button>
            <button
              type="button"
              onClick={() => {
                logout();
                setDropdownOpen(false);
              }}
              className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-left text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Đăng xuất</span>
            </button>
          </div>
        </div>
      )}

      {/* 3. Login Modal */}
      {showLoginModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div
            style={{ backgroundColor: '#131B2A' }}
            className="border border-[#2B394E] rounded-2xl max-w-sm w-full p-6 shadow-2xl space-y-4"
          >
            <div className="flex items-center gap-2.5 text-brand-gold font-bold text-sm">
              <div className="p-1.5 rounded-lg bg-brand-gold/15 text-brand-gold border border-brand-gold/30">
                <Lock className="w-4 h-4" />
              </div>
              <span>Đăng nhập hệ thống CrowdSight</span>
            </div>

            <form onSubmit={handleRealLogin} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-brand-text-muted mb-1 font-medium">Tên đăng nhập</label>
                <input
                  type="text"
                  required
                  value={usernameInput}
                  onChange={(e) => setUsernameInput(e.target.value)}
                  placeholder="admin / operator / viewer"
                  style={{ backgroundColor: '#101622' }}
                  className="w-full border border-[#2B394E] rounded-lg px-3 py-2 text-brand-text-primary focus:outline-none focus:border-brand-gold placeholder:text-brand-text-muted/50"
                />
              </div>

              <div>
                <label className="block text-brand-text-muted mb-1 font-medium">Mật khẩu</label>
                <input
                  type="password"
                  required
                  value={passwordInput}
                  onChange={(e) => setPasswordInput(e.target.value)}
                  placeholder="admin123 / operator123 / viewer123"
                  style={{ backgroundColor: '#101622' }}
                  className="w-full border border-[#2B394E] rounded-lg px-3 py-2 text-brand-text-primary focus:outline-none focus:border-brand-gold placeholder:text-brand-text-muted/50"
                />
              </div>

              {loginError && (
                <div className="p-2.5 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-[11px]">
                  {loginError}
                </div>
              )}

              <div
                style={{ backgroundColor: '#101724' }}
                className="p-3 rounded-xl border border-[#202C3E] text-[10px] text-brand-text-muted space-y-1"
              >
                <p className="font-semibold text-brand-gold">Tài khoản mẫu có sẵn:</p>
                <p>• Admin: <code className="text-brand-text-primary font-mono">admin</code> / <code className="text-brand-text-primary font-mono">admin123</code></p>
                <p>• Operator: <code className="text-brand-text-primary font-mono">operator</code> / <code className="text-brand-text-primary font-mono">operator123</code></p>
                <p>• Viewer: <code className="text-brand-text-primary font-mono">viewer</code> / <code className="text-brand-text-primary font-mono">viewer123</code></p>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowLoginModal(false)}
                  className="px-3.5 py-1.5 rounded-lg bg-[#182335] border border-[#2B394E] text-brand-text-muted hover:text-brand-text-primary transition-colors cursor-pointer"
                >
                  Đóng
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="px-4 py-1.5 rounded-lg bg-brand-gold text-brand-abyssal font-bold hover:bg-brand-gold/90 transition-colors cursor-pointer disabled:opacity-50"
                >
                  {isLoading ? 'Đang xác thực...' : 'Đăng nhập'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
