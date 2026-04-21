import axios from 'axios';
import { getInitDataRaw } from './telegram';

export const api = axios.create({
  baseURL: '/api/miniapp',
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const initData = getInitDataRaw();
  if (initData) {
    config.headers.set('X-Telegram-Init-Data', initData);
  }
  return config;
});

export interface Transaction {
  id: number;
  type: 'expense' | 'income';
  amount: number;
  currency: string;
  category: string;
  description?: string | null;
  date: string;
  created_at?: string;
}

export interface DashboardData {
  balance: number;
  income_month: number;
  expense_month: number;
  currency: string;
  recent: Transaction[];
}

export interface CategorySummary {
  category: string;
  total: number;
}

export interface Me {
  id: number;
  first_name?: string;
  username?: string;
  plan: { plan: string; is_premium: boolean; expires_at?: string | null };
}

export const API = {
  me: () => api.get<Me>('/me').then((r) => r.data),
  dashboard: () => api.get<DashboardData>('/dashboard').then((r) => r.data),
  listTransactions: (params: { limit?: number; offset?: number; q?: string } = {}) =>
    api.get<Transaction[]>('/transactions', { params }).then((r) => r.data),
  createTransaction: (body: {
    type: 'expense' | 'income';
    amount: number;
    currency?: string;
    category: string;
    description?: string;
    date?: string;
  }) => api.post<Transaction>('/transactions', body).then((r) => r.data),
  deleteTransaction: (id: number) =>
    api.delete(`/transactions/${id}`).then(() => true),
  categoriesSummary: (period: 'month' | 'year' | 'all' = 'month') =>
    api
      .get<CategorySummary[]>('/categories/summary', { params: { period } })
      .then((r) => r.data),
};
