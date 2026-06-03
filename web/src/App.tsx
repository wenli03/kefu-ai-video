import { Routes, Route, Navigate, NavLink } from 'react-router-dom';
import { CustomerPage } from './pages/CustomerPage';
import { AgentPage } from './pages/AgentPage';
import { AdminPage } from './pages/AdminPage';

export default function App() {
  return (
    <div className="app">
      <nav className="top-nav">
        <NavLink to="/customer" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          客户端
        </NavLink>
        <NavLink to="/agent" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          坐席端
        </NavLink>
        <NavLink to="/admin" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          管理端
        </NavLink>
      </nav>
      <main className="main-content">
        <Routes>
          <Route path="/customer" element={<CustomerPage />} />
          <Route path="/agent" element={<AgentPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="*" element={<Navigate to="/customer" replace />} />
        </Routes>
      </main>
    </div>
  );
}
