import { Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Transactions from './pages/Transactions';
import AddTransaction from './pages/AddTransaction';
import BottomNav from './components/BottomNav';

export default function App() {
  return (
    <div className="min-h-screen flex flex-col bg-tg-bg text-tg-text">
      <main className="flex-1 pb-20">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/add" element={<AddTransaction />} />
        </Routes>
      </main>
      <BottomNav />
    </div>
  );
}
