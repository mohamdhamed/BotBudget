import { NavLink } from 'react-router-dom';

const tabs = [
  { to: '/dashboard', label: 'الرئيسية', icon: '🏠' },
  { to: '/transactions', label: 'المعاملات', icon: '📋' },
  { to: '/add', label: 'إضافة', icon: '➕' },
];

export default function BottomNav() {
  return (
    <nav
      className="fixed bottom-0 inset-x-0 h-16 grid grid-cols-3 border-t border-black/10"
      style={{ background: 'var(--tg-theme-secondary-bg-color)' }}
    >
      {tabs.map((t) => (
        <NavLink
          key={t.to}
          to={t.to}
          className={({ isActive }) =>
            `flex flex-col items-center justify-center text-xs gap-0.5 ${
              isActive ? 'text-tg-link font-semibold' : 'text-tg-hint'
            }`
          }
        >
          <span className="text-xl leading-none">{t.icon}</span>
          <span>{t.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
