import { useEffect, useState } from 'react';
import { API, Transaction } from '../lib/api';

function fmt(n: number, currency = 'EUR') {
  return new Intl.NumberFormat('ar', { style: 'currency', currency }).format(n);
}

export default function Transactions() {
  const [items, setItems] = useState<Transaction[]>([]);
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = (query?: string) => {
    setLoading(true);
    API.listTransactions({ limit: 100, q: query || undefined })
      .then(setItems)
      .catch((e) => setErr(e?.response?.data?.detail || e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const onSearch = (e: React.FormEvent) => {
    e.preventDefault();
    load(q);
  };

  const onDelete = async (id: number) => {
    if (!confirm('حذف هذه المعاملة؟')) return;
    try {
      await API.deleteTransaction(id);
      setItems((xs) => xs.filter((x) => x.id !== id));
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'فشل الحذف');
    }
  };

  return (
    <div className="p-4 space-y-4">
      <form onSubmit={onSearch} className="flex gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="بحث..."
          className="flex-1 rounded-xl px-3 py-2 outline-none border border-black/10"
          style={{ background: 'var(--tg-theme-secondary-bg-color)' }}
        />
        <button
          type="submit"
          className="rounded-xl px-4 py-2 text-tg-button-text"
          style={{ background: 'var(--tg-theme-button-color)' }}
        >
          بحث
        </button>
      </form>

      {err && <div className="text-red-500 text-sm">{err}</div>}
      {loading && <div className="text-tg-hint">جاري التحميل...</div>}

      <ul className="space-y-2">
        {items.map((t) => (
          <li
            key={t.id}
            className="flex justify-between items-center rounded-xl p-3"
            style={{ background: 'var(--tg-theme-secondary-bg-color)' }}
          >
            <div className="min-w-0">
              <div className="font-medium truncate">{t.category}</div>
              <div className="text-xs text-tg-hint truncate">
                {t.description || t.date}
              </div>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <span className={t.type === 'expense' ? 'text-red-500' : 'text-green-500'}>
                {t.type === 'expense' ? '-' : '+'}
                {fmt(t.amount, t.currency)}
              </span>
              <button
                onClick={() => onDelete(t.id)}
                className="text-red-500 text-sm"
                aria-label="حذف"
              >
                🗑️
              </button>
            </div>
          </li>
        ))}
        {!loading && items.length === 0 && (
          <li className="text-tg-hint text-sm">لا توجد نتائج</li>
        )}
      </ul>
    </div>
  );
}
