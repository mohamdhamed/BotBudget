import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { API } from '../lib/api';

const CATEGORIES = [
  'طعام',
  'مواصلات',
  'تسوق',
  'فواتير',
  'ترفيه',
  'صحة',
  'تعليم',
  'إيجار',
  'راتب',
  'أخرى',
];

export default function AddTransaction() {
  const nav = useNavigate();
  const [type, setType] = useState<'expense' | 'income'>('expense');
  const [amount, setAmount] = useState('');
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [description, setDescription] = useState('');
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [currency, setCurrency] = useState('EUR');
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const n = parseFloat(amount);
    if (!n || n <= 0) {
      setErr('أدخل مبلغًا صحيحًا');
      return;
    }
    setSubmitting(true);
    setErr(null);
    try {
      await API.createTransaction({
        type,
        amount: n,
        currency,
        category,
        description: description || undefined,
        date,
      });
      nav('/dashboard');
    } catch (e: any) {
      setErr(e?.response?.data?.detail || 'فشل الحفظ');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="p-4 space-y-4">
      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={() => setType('expense')}
          className={`rounded-xl py-3 font-semibold ${
            type === 'expense' ? 'text-white bg-red-500' : 'text-tg-hint'
          }`}
          style={type !== 'expense' ? { background: 'var(--tg-theme-secondary-bg-color)' } : {}}
        >
          مصروف
        </button>
        <button
          type="button"
          onClick={() => setType('income')}
          className={`rounded-xl py-3 font-semibold ${
            type === 'income' ? 'text-white bg-green-500' : 'text-tg-hint'
          }`}
          style={type !== 'income' ? { background: 'var(--tg-theme-secondary-bg-color)' } : {}}
        >
          دخل
        </button>
      </div>

      <div>
        <label className="text-sm text-tg-hint">المبلغ</label>
        <input
          type="number"
          inputMode="decimal"
          step="0.01"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          className="w-full mt-1 rounded-xl px-3 py-2 border border-black/10"
          style={{ background: 'var(--tg-theme-secondary-bg-color)' }}
          required
        />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-sm text-tg-hint">العملة</label>
          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            className="w-full mt-1 rounded-xl px-3 py-2 border border-black/10"
            style={{ background: 'var(--tg-theme-secondary-bg-color)' }}
          >
            <option value="EUR">EUR</option>
            <option value="USD">USD</option>
            <option value="SAR">SAR</option>
            <option value="AED">AED</option>
            <option value="EGP">EGP</option>
          </select>
        </div>
        <div>
          <label className="text-sm text-tg-hint">الفئة</label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full mt-1 rounded-xl px-3 py-2 border border-black/10"
            style={{ background: 'var(--tg-theme-secondary-bg-color)' }}
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="text-sm text-tg-hint">التاريخ</label>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="w-full mt-1 rounded-xl px-3 py-2 border border-black/10"
          style={{ background: 'var(--tg-theme-secondary-bg-color)' }}
        />
      </div>

      <div>
        <label className="text-sm text-tg-hint">ملاحظة</label>
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full mt-1 rounded-xl px-3 py-2 border border-black/10"
          style={{ background: 'var(--tg-theme-secondary-bg-color)' }}
        />
      </div>

      {err && <div className="text-red-500 text-sm">{err}</div>}

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-xl py-3 font-semibold disabled:opacity-50"
        style={{
          background: 'var(--tg-theme-button-color)',
          color: 'var(--tg-theme-button-text-color)',
        }}
      >
        {submitting ? 'جاري الحفظ...' : 'حفظ'}
      </button>
    </form>
  );
}
