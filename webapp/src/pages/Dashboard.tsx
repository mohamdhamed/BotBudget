import { useEffect, useState } from 'react';
import { API, DashboardData, CategorySummary } from '../lib/api';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

const COLORS = ['#2481cc', '#34c759', '#ff9500', '#ff3b30', '#af52de', '#ffcc00', '#5ac8fa'];

function fmt(n: number, currency = 'EUR') {
  return new Intl.NumberFormat('ar', { style: 'currency', currency }).format(n);
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [cats, setCats] = useState<CategorySummary[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([API.dashboard(), API.categoriesSummary('month')])
      .then(([d, c]) => {
        setData(d);
        setCats(c);
      })
      .catch((e) => setErr(e?.response?.data?.detail || e.message));
  }, []);

  if (err) return <div className="p-4 text-red-500">خطأ: {err}</div>;
  if (!data) return <div className="p-4 text-tg-hint">جاري التحميل...</div>;

  const cur = data.currency || 'EUR';

  return (
    <div className="p-4 space-y-4">
      <div
        className="rounded-2xl p-5 shadow-sm"
        style={{ background: 'var(--tg-theme-secondary-bg-color)' }}
      >
        <div className="text-sm text-tg-hint">الرصيد</div>
        <div className="text-3xl font-bold mt-1">{fmt(data.balance, cur)}</div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div
          className="rounded-2xl p-4"
          style={{ background: 'var(--tg-theme-secondary-bg-color)' }}
        >
          <div className="text-xs text-tg-hint">الدخل (الشهر)</div>
          <div className="text-lg font-semibold text-green-500 mt-1">
            {fmt(data.income_month, cur)}
          </div>
        </div>
        <div
          className="rounded-2xl p-4"
          style={{ background: 'var(--tg-theme-secondary-bg-color)' }}
        >
          <div className="text-xs text-tg-hint">المصاريف (الشهر)</div>
          <div className="text-lg font-semibold text-red-500 mt-1">
            {fmt(data.expense_month, cur)}
          </div>
        </div>
      </div>

      {cats.length > 0 && (
        <div
          className="rounded-2xl p-4"
          style={{ background: 'var(--tg-theme-secondary-bg-color)' }}
        >
          <div className="text-sm text-tg-hint mb-2">الفئات (الشهر)</div>
          <div style={{ width: '100%', height: 220 }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={cats}
                  dataKey="total"
                  nameKey="category"
                  outerRadius={80}
                  label={(e) => e.category}
                >
                  {cats.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number) => fmt(v, cur)} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div>
        <div className="text-sm text-tg-hint mb-2">أحدث المعاملات</div>
        <ul className="space-y-2">
          {data.recent.map((t) => (
            <li
              key={t.id}
              className="flex justify-between items-center rounded-xl p-3"
              style={{ background: 'var(--tg-theme-secondary-bg-color)' }}
            >
              <div>
                <div className="font-medium">{t.category}</div>
                <div className="text-xs text-tg-hint">{t.description || t.date}</div>
              </div>
              <div
                className={t.type === 'expense' ? 'text-red-500' : 'text-green-500'}
              >
                {t.type === 'expense' ? '-' : '+'}
                {fmt(t.amount, t.currency)}
              </div>
            </li>
          ))}
          {data.recent.length === 0 && (
            <li className="text-tg-hint text-sm">لا توجد معاملات بعد</li>
          )}
        </ul>
      </div>
    </div>
  );
}
