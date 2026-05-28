import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Upload, ClipboardCheck, LogOut, Leaf, ChevronLeft, ChevronRight } from 'lucide-react';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/upload', label: 'Upload Data', icon: Upload },
  { path: '/review', label: 'Review & Approve', icon: ClipboardCheck },
];

export default function Layout({ children, user, onLogout }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [isCollapsed, setIsCollapsed] = useState(() => {
    return localStorage.getItem('sidebar-collapsed') === 'true';
  });

  const toggleSidebar = () => {
    setIsCollapsed(prev => {
      const next = !prev;
      localStorage.setItem('sidebar-collapsed', String(next));
      return next;
    });
  };

  return (
    <div className={`app-layout ${isCollapsed ? 'sidebar-collapsed' : ''}`}>
      <aside className="sidebar">
        {/* Toggle Button */}
        <button
          onClick={toggleSidebar}
          aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={isCollapsed ? "Expand" : "Collapse"}
          style={{
            position: 'absolute',
            right: '-12px',
            top: '26px',
            width: '24px',
            height: '24px',
            borderRadius: '50%',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            boxShadow: 'var(--shadow-sm)',
            color: 'var(--text-secondary)',
            zIndex: 100,
            transition: 'all var(--duration-fast) var(--ease)',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.color = 'var(--brand-dark)';
            e.currentTarget.style.transform = 'scale(1.1)';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.color = 'var(--text-secondary)';
            e.currentTarget.style.transform = 'scale(1)';
          }}
        >
          {isCollapsed ? <ChevronRight size={13} /> : <ChevronLeft size={13} />}
        </button>

        {/* Logo */}
        <div className="sidebar-logo">
          <div className="logo-icon">
            <Leaf size={18} color="white" />
          </div>
          <h1>Breathe ESG</h1>
        </div>

        {/* Nav section label */}
        <div className="sidebar-section-label" style={{
          fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-muted)',
          textTransform: 'uppercase', letterSpacing: '0.06em',
          padding: '0 var(--sp-3)',
          marginBottom: 'var(--sp-2)',
        }}>
          Main
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav" role="navigation" aria-label="Main navigation">
          {navItems.map(({ path, label, icon: Icon }) => {
            const isActive = location.pathname === path;
            return (
              <button
                key={path}
                className={`nav-link ${isActive ? 'active' : ''}`}
                onClick={() => navigate(path)}
                aria-current={isActive ? 'page' : undefined}
                title={isCollapsed ? label : undefined}
              >
                <Icon size={17} />
                <span>{label}</span>
              </button>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="sidebar-footer">
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: isCollapsed ? 'var(--sp-2)' : 'var(--sp-3)',
            padding: 'var(--sp-2)',
            flexDirection: isCollapsed ? 'column' : 'row',
            justifyContent: 'center',
          }}>
            <div className="user-avatar" title={`${user?.username} (${user?.role || 'Analyst'})`}>
              {(user?.username || 'U')[0].toUpperCase()}
            </div>
            {!isCollapsed && (
              <div className="user-details" style={{ flex: 1, minWidth: 0 }}>
                <div className="user-name">{user?.username}</div>
                <div className="user-role">
                  {user?.role || 'Analyst'}
                </div>
              </div>
            )}
            <button
              onClick={onLogout}
              aria-label="Log out"
              title="Log out"
              style={{
                background: 'none', border: 'none',
                color: 'var(--text-muted)', cursor: 'pointer',
                padding: 'var(--sp-1)', borderRadius: 'var(--r-md)',
                display: 'flex', transition: 'color var(--duration-fast)',
                marginTop: isCollapsed ? 'var(--sp-2)' : '0',
              }}
              onMouseEnter={e => e.currentTarget.style.color = 'var(--danger)'}
              onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="main-content animate-fade-in">
        {children}
      </main>
    </div>
  );
}
