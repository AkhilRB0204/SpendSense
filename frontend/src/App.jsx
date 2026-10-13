import React, { useState, useEffect, useRef } from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import {
  DollarSign, TrendingUp, Calendar, CreditCard, MessageCircle,
  PlusCircle, Target, Menu, X, LogOut, Send, Trash2, Download,
  Search, ChevronLeft, ChevronRight, AlertTriangle, Bookmark, Check
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const TEMPLATES_KEY = 'spendsense_templates';
const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6'];

function getAuthHeaders() {
  const token = localStorage.getItem('access_token');
  return {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` })
  };
}

function handle401(response) {
  if (response.status === 401) {
    localStorage.removeItem('access_token');
    window.location.reload();
  }
  return response;
}

function validatePassword(password) {
  const errors = [];
  if (password.length < 8) errors.push("Password must be at least 8 characters");
  if (!/[A-Z]/.test(password)) errors.push("Need uppercase letter");
  if (!/[a-z]/.test(password)) errors.push("Need lowercase letter");
  if (!/\d/.test(password)) errors.push("Need at least one digit");
  if (!/[!@#$%^&*(),.?":{}|<>_/-]/.test(password)) errors.push("Need special character");
  return { valid: errors.length === 0, errors };
}

function validateEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// ── API ────────────────────────────────────────────────────────────────────

async function login(email, password) {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);
  const response = await fetch(`${API_BASE}/users/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData
  });
  if (!response.ok) { const e = await response.json(); throw new Error(e.detail || 'Login failed'); }
  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
  return data;
}

async function register(name, email, password) {
  const response = await fetch(`${API_BASE}/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password })
  });
  if (!response.ok) { const e = await response.json(); throw new Error(e.detail || 'Registration failed'); }
  return await response.json();
}

async function getCurrentUser() {
  const token = localStorage.getItem('access_token');
  if (!token) throw new Error('No token');
  const response = await fetch(`${API_BASE}/users/me`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error('Failed to fetch user');
  return await response.json();
}

async function fetchExpenses() {
  const response = handle401(await fetch(`${API_BASE}/expenses`, { headers: getAuthHeaders() }));
  if (!response.ok) throw new Error('Failed to fetch expenses');
  return await response.json();
}

async function createExpense(category_id, amount, description, created_at) {
  const body = { category_id, amount, description };
  if (created_at) body.created_at = created_at;
  const response = handle401(await fetch(`${API_BASE}/expenses`, {
    method: 'POST', headers: getAuthHeaders(), body: JSON.stringify(body)
  }));
  if (!response.ok) { const e = await response.json(); throw new Error(e.detail || 'Failed to create expense'); }
  return await response.json();
}

async function deleteExpense(expenseId) {
  const response = await fetch(`${API_BASE}/expenses/${expenseId}`, { method: 'DELETE', headers: getAuthHeaders() });
  if (!response.ok) throw new Error('Failed to delete expense');
  return await response.json();
}

async function fetchCategories() {
  const response = await fetch(`${API_BASE}/categories`, { headers: { 'Content-Type': 'application/json' } });
  if (!response.ok) throw new Error('Failed to fetch categories');
  return await response.json();
}

async function createCategory(name) {
  const response = await fetch(`${API_BASE}/categories`, {
    method: 'POST', headers: getAuthHeaders(), body: JSON.stringify({ name })
  });
  if (!response.ok) { const e = await response.json(); throw new Error(e.detail || 'Failed to create category'); }
  return await response.json();
}

async function fetchExpenseSummary(month, year) {
  const response = await fetch(`${API_BASE}/expenses/summary?month=${month}&year=${year}`, { headers: getAuthHeaders() });
  if (!response.ok) throw new Error('Failed to fetch summary');
  return await response.json();
}

async function fetchMonthlyTrend(months = 6) {
  const response = handle401(await fetch(`${API_BASE}/expenses/trend?months=${months}`, { headers: getAuthHeaders() }));
  if (!response.ok) throw new Error('Failed to fetch trend');
  return await response.json();
}

async function fetchBudgetStatus() {
  const response = handle401(await fetch(`${API_BASE}/budgets/status`, { headers: getAuthHeaders() }));
  if (!response.ok) throw new Error('Failed to fetch budget status');
  return await response.json();
}

async function createBudget(category_id, amount, period, alert_threshold) {
  const response = await fetch(`${API_BASE}/budgets`, {
    method: 'POST', headers: getAuthHeaders(),
    body: JSON.stringify({ category_id: category_id || null, amount, period, alert_threshold })
  });
  if (!response.ok) { const e = await response.json(); throw new Error(e.detail || 'Failed to create budget'); }
  return await response.json();
}

async function deleteBudget(budgetId) {
  const response = await fetch(`${API_BASE}/budgets/${budgetId}`, { method: 'DELETE', headers: getAuthHeaders() });
  if (!response.ok) throw new Error('Failed to delete budget');
  return await response.json();
}

async function queryAI(query, context = []) {
  const response = await fetch(`${API_BASE}/ai/query`, {
    method: 'POST', headers: getAuthHeaders(), body: JSON.stringify({ query, context })
  });
  if (response.status === 401) { localStorage.removeItem('access_token'); window.location.reload(); return; }
  if (!response.ok) { const e = await response.json(); throw new Error(e.detail || 'Failed to query AI'); }
  return await response.json();
}

async function loadChatHistory(userId) {
  const response = await fetch(`${API_BASE}/users/${userId}/chat`, { headers: getAuthHeaders() });
  if (!response.ok) return [];
  return await response.json();
}

async function saveChatMessage(userId, sender, message) {
  await fetch(`${API_BASE}/users/${userId}/chat`, {
    method: 'POST', headers: getAuthHeaders(),
    body: JSON.stringify({ user_id: userId, sender, message })
  });
}

// ── Utilities ──────────────────────────────────────────────────────────────

function exportToCSV(expenses, categories) {
  const catMap = {};
  categories.forEach(c => { catMap[c.category_id] = c.name; });
  const rows = [['Date', 'Description', 'Category', 'Amount']];
  expenses.forEach(e => rows.push([
    new Date(e.expense_date).toLocaleDateString(),
    `"${(e.description || '').replace(/"/g, '""')}"`,
    catMap[e.category_id] || 'Unknown',
    e.amount.toFixed(2)
  ]));
  const csv = rows.map(r => r.join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `expenses-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function getTemplates() {
  try { return JSON.parse(localStorage.getItem(TEMPLATES_KEY) || '[]'); } catch { return []; }
}
function saveTemplates(t) { localStorage.setItem(TEMPLATES_KEY, JSON.stringify(t)); }

// ── App ────────────────────────────────────────────────────────────────────

export default function App() {
  const [currentPage, setCurrentPage] = useState('login');
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { checkAuth(); }, []);

  const checkAuth = async () => {
    try {
      const userData = await getCurrentUser();
      setUser(userData);
      setCurrentPage('dashboard');
    } catch { /* not authenticated */ } finally { setLoading(false); }
  };

  if (loading) return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-gray-600">Loading...</p>
      </div>
    </div>
  );

  if (!user) return <AuthPage onLogin={(u) => { setUser(u); setCurrentPage('dashboard'); }} />;

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      <Navigation currentPage={currentPage} setCurrentPage={setCurrentPage}
        onLogout={() => { localStorage.removeItem('access_token'); setUser(null); setCurrentPage('login'); }}
        user={user} />
      <main className="max-w-7xl mx-auto px-4 py-8">
        {currentPage === 'dashboard' && <Dashboard user={user} />}
        {currentPage === 'expenses'  && <Expenses  user={user} />}
        {currentPage === 'budgets'   && <Budgets   user={user} />}
        {currentPage === 'ai-chat'   && <AIChat    user={user} />}
      </main>
    </div>
  );
}

// ── Navigation ─────────────────────────────────────────────────────────────

function Navigation({ currentPage, setCurrentPage, onLogout, user }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navItems = [
    { id: 'dashboard', label: 'Dashboard',    icon: TrendingUp },
    { id: 'expenses',  label: 'Expenses',     icon: DollarSign },
    { id: 'budgets',   label: 'Budgets',      icon: Target },
    { id: 'ai-chat',   label: 'AI Assistant', icon: MessageCircle }
  ];
  return (
    <nav className="bg-white shadow-lg sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-indigo-600 to-purple-600 rounded-lg flex items-center justify-center">
              <DollarSign className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">SpendSense</span>
          </div>

          <div className="hidden md:flex items-center space-x-1">
            {navItems.map(({ id, label, icon: Icon }) => (
              <button key={id} onClick={() => setCurrentPage(id)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition ${currentPage === id ? 'bg-indigo-100 text-indigo-700' : 'text-gray-600 hover:bg-gray-100'}`}>
                <Icon className="w-5 h-5" /><span className="font-medium">{label}</span>
              </button>
            ))}
          </div>

          <div className="hidden md:flex items-center space-x-3">
            <span className="text-sm text-gray-600">{user?.name || 'User'}</span>
            <button onClick={onLogout} className="flex items-center space-x-2 px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition">
              <LogOut className="w-4 h-4" /><span>Logout</span>
            </button>
          </div>

          <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="md:hidden p-2 rounded-lg hover:bg-gray-100">
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {mobileMenuOpen && (
          <div className="md:hidden py-4 border-t">
            {navItems.map(({ id, label, icon: Icon }) => (
              <button key={id} onClick={() => { setCurrentPage(id); setMobileMenuOpen(false); }}
                className={`flex items-center space-x-3 w-full px-4 py-3 rounded-lg transition ${currentPage === id ? 'bg-indigo-100 text-indigo-700' : 'text-gray-600 hover:bg-gray-100'}`}>
                <Icon className="w-5 h-5" /><span className="font-medium">{label}</span>
              </button>
            ))}
            <button onClick={onLogout} className="flex items-center space-x-3 w-full px-4 py-3 text-red-600 hover:bg-red-50 rounded-lg transition mt-2">
              <LogOut className="w-5 h-5" /><span className="font-medium">Logout</span>
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}

// ── Auth ───────────────────────────────────────────────────────────────────

function AuthPage({ onLogin }) {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({ name: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [passwordErrors, setPasswordErrors] = useState([]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (isLogin) {
        await login(formData.email, formData.password);
        const userData = await getCurrentUser();
        onLogin(userData);
      } else {
        if (!validateEmail(formData.email)) { setError('Invalid email format'); setLoading(false); return; }
        const v = validatePassword(formData.password);
        if (!v.valid) { setError(v.errors[0]); setLoading(false); return; }
        await register(formData.name, formData.email, formData.password);
        setIsLogin(true);
        setError('Account created! Please login.');
      }
    } catch (err) { setError(err.message || 'An error occurred'); }
    finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-br from-indigo-600 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <DollarSign className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">SpendSense AI</h1>
          <p className="text-gray-600 mt-2">Smart expense tracking with AI insights</p>
        </div>

        <div className="flex gap-2 mb-6">
          {['Login', 'Sign Up'].map((label, i) => (
            <button key={label} onClick={() => { setIsLogin(i === 0); setPasswordErrors([]); setError(''); }}
              className={`flex-1 py-2 rounded-lg font-medium transition ${(i === 0) === isLogin ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600'}`}>
              {label}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <input type="text" placeholder="Full Name" value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent" required />
          )}
          <input type="email" placeholder="Email" value={formData.email}
            onChange={e => setFormData({ ...formData, email: e.target.value })}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent" required />
          <input type="password" placeholder="Password" value={formData.password}
            onChange={e => {
              setFormData({ ...formData, password: e.target.value });
              if (!isLogin) setPasswordErrors(validatePassword(e.target.value).errors);
            }}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent" required />
          {!isLogin && passwordErrors.length > 0 && (
            <div className="text-xs text-gray-600 space-y-1">{passwordErrors.map((err, i) => <div key={i}>• {err}</div>)}</div>
          )}
          {error && (
            <div className={`p-3 rounded-lg text-sm ${error.includes('created') ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>{error}</div>
          )}
          <button type="submit" disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-medium hover:shadow-lg transition disabled:opacity-50">
            {loading ? 'Please wait...' : isLogin ? 'Login' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  );
}

// ── Dashboard ──────────────────────────────────────────────────────────────

function Dashboard({ user }) {
  const now = new Date();
  const [selectedMonth, setSelectedMonth] = useState(now.getMonth() + 1);
  const [selectedYear, setSelectedYear]   = useState(now.getFullYear());
  const [stats, setStats]           = useState(null);
  const [trendData, setTrendData]   = useState([]);
  const [trendMonths, setTrendMonths] = useState(6);
  const [budgetAlerts, setBudgetAlerts] = useState([]);
  const [loading, setLoading]       = useState(true);

  useEffect(() => { loadDashboard(); }, [selectedMonth, selectedYear]);
  useEffect(() => {
    fetchMonthlyTrend(trendMonths)
      .then(trend => setTrendData(trend.trend || []))
      .catch(err => console.error('Trend load failed:', err));
  }, [trendMonths]);

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const [summary, budgets] = await Promise.all([
        fetchExpenseSummary(selectedMonth, selectedYear),
        fetchBudgetStatus()
      ]);
      setStats(summary);
      setBudgetAlerts(budgets.filter(b => b.is_over_budget || b.should_alert));
    } catch (err) { console.error('Dashboard load failed:', err); }
    finally { setLoading(false); }
  };

  const prevMonth = () => {
    if (selectedMonth === 1) { setSelectedMonth(12); setSelectedYear(y => y - 1); }
    else setSelectedMonth(m => m - 1);
  };
  const nextMonth = () => {
    const isCurrentMonth = selectedYear === now.getFullYear() && selectedMonth === now.getMonth() + 1;
    if (isCurrentMonth) return;
    if (selectedMonth === 12) { setSelectedMonth(1); setSelectedYear(y => y + 1); }
    else setSelectedMonth(m => m + 1);
  };

  const monthLabel = new Date(selectedYear, selectedMonth - 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  const categoryData = stats?.by_category ? Object.entries(stats.by_category).map(([name, value]) => ({ name, value })) : [];
  const isCurrentMonth = selectedYear === now.getFullYear() && selectedMonth === now.getMonth() + 1;

  if (loading) return <div className="text-center py-12 text-gray-500">Loading dashboard...</div>;

  return (
    <div className="space-y-6">
      {/* Budget alert banners */}
      {budgetAlerts.length > 0 && (
        <div className="space-y-2">
          {budgetAlerts.map(b => (
            <div key={b.budget_id}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium ${b.is_over_budget ? 'bg-red-50 border border-red-200 text-red-800' : 'bg-yellow-50 border border-yellow-200 text-yellow-800'}`}>
              <AlertTriangle className="w-5 h-5 flex-shrink-0" />
              {b.is_over_budget
                ? `Over budget on ${b.category_name || 'Overall'}: spent $${b.spent_amount.toFixed(2)} of $${b.budget_amount.toFixed(2)}`
                : `Approaching limit on ${b.category_name || 'Overall'}: ${b.percentage_used.toFixed(0)}% used ($${b.remaining_amount.toFixed(2)} left)`}
            </div>
          ))}
        </div>
      )}

      {/* Title + month picker */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <div className="flex items-center gap-2">
          <button onClick={prevMonth} className="p-2 rounded-lg hover:bg-gray-100 transition">
            <ChevronLeft className="w-5 h-5 text-gray-600" />
          </button>
          <span className="text-sm font-medium text-gray-700 min-w-[140px] text-center">{monthLabel}</span>
          <button onClick={nextMonth} disabled={isCurrentMonth}
            className="p-2 rounded-lg hover:bg-gray-100 transition disabled:opacity-30">
            <ChevronRight className="w-5 h-5 text-gray-600" />
          </button>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl p-6 text-white shadow-lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium opacity-90">Total Spending</h3>
            <DollarSign className="w-8 h-8 opacity-80" />
          </div>
          <p className="text-3xl font-bold">${stats?.total_expense?.toFixed(2) || '0.00'}</p>
          <p className="text-sm opacity-80 mt-2">{monthLabel}</p>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-lg border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-600">Daily Average</h3>
            <Calendar className="w-8 h-8 text-indigo-500" />
          </div>
          <p className="text-3xl font-bold text-gray-900">${stats?.average_per_day?.toFixed(2) || '0.00'}</p>
          <p className="text-sm text-gray-500 mt-2">{stats?.total_days || 0} days tracked</p>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-lg border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-600">Categories</h3>
            <CreditCard className="w-8 h-8 text-purple-500" />
          </div>
          <p className="text-3xl font-bold text-gray-900">{categoryData.length}</p>
          <p className="text-sm text-gray-500 mt-2">Active this month</p>
        </div>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl p-6 shadow-lg border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Spending by Category</h3>
          {categoryData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={categoryData} cx="50%" cy="50%" outerRadius={100}
                  labelLine={false} label={({ name, value }) => `${name}: $${value.toFixed(0)}`}
                  dataKey="value">
                  {categoryData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={v => [`$${Number(v).toFixed(2)}`, 'Spent']} />
              </PieChart>
            </ResponsiveContainer>
          ) : <div className="text-center text-gray-400 py-20">No expenses this month</div>}
        </div>

        <div className="bg-white rounded-xl p-6 shadow-lg border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Category Breakdown</h3>
          {categoryData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={categoryData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tickFormatter={v => `$${v}`} tick={{ fontSize: 12 }} />
                <Tooltip formatter={v => [`$${Number(v).toFixed(2)}`, 'Spent']} />
                <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <div className="text-center text-gray-400 py-20">No expenses this month</div>}
        </div>
      </div>

      {/* Monthly trend line chart */}
      <div className="bg-white rounded-xl p-6 shadow-lg border border-gray-100">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Monthly Spending</h3>
          <div className="flex gap-1">
            {[6, 12].map(n => (
              <button key={n} onClick={() => setTrendMonths(n)}
                className={`px-3 py-1 rounded-lg text-sm font-medium ${trendMonths === n ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                {n}M
              </button>
            ))}
          </div>
        </div>
        {trendData.length > 0 ? (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={trendData} margin={{ top: 8, right: 24, left: 0, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={v => `$${v}`} tick={{ fontSize: 12 }} />
              <Tooltip formatter={v => [`$${Number(v).toFixed(2)}`, 'Spending']} />
              <Line type="monotone" dataKey="total" stroke="#6366f1" strokeWidth={2.5}
                dot={{ r: 4, fill: '#6366f1' }} activeDot={{ r: 6 }} />
            </LineChart>
          </ResponsiveContainer>
        ) : <div className="text-center text-gray-400 py-16">No trend data yet</div>}
      </div>
    </div>
  );
}

// ── Expenses ───────────────────────────────────────────────────────────────

function Expenses({ user }) {
  const [expenses, setExpenses]     = useState([]);
  const [categories, setCategories] = useState([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [search, setSearch]         = useState('');
  const [filterCat, setFilterCat]   = useState('');
  const [templates, setTemplates]   = useState(getTemplates());
  const [showTemplates, setShowTemplates] = useState(false);
  const [formData, setFormData]     = useState({ category_id: '', amount: '', description: '', created_at: '' });

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [e, c] = await Promise.all([fetchExpenses(), fetchCategories()]);
      setExpenses(e);
      setCategories(c);
    } catch (err) { console.error(err); }
  };

  const catMap = {};
  categories.forEach(c => { catMap[c.category_id] = c.name; });

  const filtered = expenses.filter(e => {
    const matchSearch = !search || e.description.toLowerCase().includes(search.toLowerCase());
    const matchCat = !filterCat || String(e.category_id) === filterCat;
    return matchSearch && matchCat;
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await createExpense(parseInt(formData.category_id), parseFloat(formData.amount), formData.description, formData.created_at || undefined);
      setShowAddModal(false);
      setFormData({ category_id: '', amount: '', description: '', created_at: '' });
      loadData();
    } catch (err) { alert(err.message); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this expense?')) return;
    try { await deleteExpense(id); loadData(); } catch (err) { alert(err.message); }
  };

  const saveAsTemplate = (expense) => {
    const name = window.prompt('Template name:', expense.description);
    if (!name?.trim()) return;
    const t = [...getTemplates(), { id: Date.now(), name: name.trim(), category_id: expense.category_id, amount: expense.amount, description: expense.description }];
    saveTemplates(t);
    setTemplates(t);
  };

  const applyTemplate = async (tpl) => {
    if (!window.confirm(`Add "${tpl.name}" — $${tpl.amount} — ${catMap[tpl.category_id] || 'Unknown'}?`)) return;
    try { await createExpense(tpl.category_id, tpl.amount, tpl.description); loadData(); }
    catch (err) { alert(err.message); }
  };

  const deleteTemplate = (id) => {
    const t = getTemplates().filter(t => t.id !== id);
    saveTemplates(t);
    setTemplates(t);
  };

  const addNewCategory = async () => {
    const name = prompt('New category name:');
    if (!name?.trim()) return;
    try { await createCategory(name.trim()); const c = await fetchCategories(); setCategories(c); }
    catch (err) { alert(err.message || 'Failed to create category'); }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-3xl font-bold text-gray-900 mr-auto">Expenses</h1>
        <button onClick={() => exportToCSV(filtered, categories)}
          className="flex items-center gap-2 px-4 py-2 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition text-sm font-medium">
          <Download className="w-4 h-4" /><span>Export CSV</span>
        </button>
        <button onClick={() => setShowTemplates(!showTemplates)}
          className="flex items-center gap-2 px-4 py-2 bg-purple-50 text-purple-700 rounded-lg hover:bg-purple-100 transition text-sm font-medium">
          <Bookmark className="w-4 h-4" /><span>Templates {templates.length > 0 && `(${templates.length})`}</span>
        </button>
        <button onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition">
          <PlusCircle className="w-5 h-5" /><span>Add Expense</span>
        </button>
      </div>

      {/* Quick-add templates panel */}
      {showTemplates && (
        <div className="bg-white rounded-xl p-5 shadow-lg border border-gray-100">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Quick-add Templates</h3>
          {templates.length === 0
            ? <p className="text-sm text-gray-400">No templates yet — click the bookmark icon on any expense row to save one.</p>
            : <div className="flex flex-wrap gap-2">
                {templates.map(t => (
                  <div key={t.id} className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
                    <button onClick={() => applyTemplate(t)} className="text-sm font-medium text-indigo-700 hover:text-indigo-900">
                      {t.name} <span className="text-gray-500 font-normal">${t.amount}</span>
                    </button>
                    <button onClick={() => deleteTemplate(t.id)} className="text-gray-400 hover:text-red-500">
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
          }
        </div>
      )}

      {/* Search + filter */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search expenses..."
            className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-sm" />
        </div>
        <select value={filterCat} onChange={e => setFilterCat(e.target.value)}
          className="px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-sm">
          <option value="">All Categories</option>
          {categories.map(c => <option key={c.category_id} value={c.category_id}>{c.name}</option>)}
        </select>
        {(search || filterCat) && (
          <button onClick={() => { setSearch(''); setFilterCat(''); }}
            className="px-3 py-2.5 text-sm text-gray-500 hover:text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50">
            Clear
          </button>
        )}
      </div>

      {/* Expense table */}
      <div className="bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden">
        {filtered.length === 0
          ? <div className="text-center text-gray-400 py-16">No expenses found</div>
          : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    {['Date', 'Description', 'Category', 'Amount', 'Actions'].map(h => (
                      <th key={h} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filtered.map(expense => (
                    <tr key={expense.expense_id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                        {new Date(expense.expense_date).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900">{expense.description}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-3 py-1 text-xs font-medium rounded-full bg-indigo-100 text-indigo-800">
                          {catMap[expense.category_id] || 'Unknown'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">
                        ${expense.amount.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap flex items-center gap-3">
                        <button onClick={() => saveAsTemplate(expense)} title="Save as template"
                          className="text-purple-400 hover:text-purple-700 transition">
                          <Bookmark className="w-4 h-4" />
                        </button>
                        <button onClick={() => handleDelete(expense.expense_id)} title="Delete"
                          className="text-red-400 hover:text-red-700 transition">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        }
        {filtered.length > 0 && (
          <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 text-sm text-gray-500">
            Showing {filtered.length} of {expenses.length} expenses
            {(search || filterCat) && ' (filtered)'}
          </div>
        )}
      </div>

      {/* Add expense modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Add New Expense</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                <div className="flex gap-2">
                  <select value={formData.category_id} onChange={e => setFormData({ ...formData, category_id: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500" required>
                    <option value="">Select category</option>
                    {categories.map(c => <option key={c.category_id} value={c.category_id}>{c.name}</option>)}
                  </select>
                  <button type="button" onClick={addNewCategory}
                    className="px-3 py-2 bg-indigo-100 text-indigo-700 rounded-lg hover:bg-indigo-200 font-medium text-sm whitespace-nowrap">
                    + New
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Amount ($)</label>
                <input type="number" step="0.01" value={formData.amount}
                  onChange={e => setFormData({ ...formData, amount: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <input type="text" value={formData.description}
                  onChange={e => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Date (MM/DD/YYYY) — optional</label>
                <input type="text" placeholder="01/13/2026" value={formData.created_at}
                  onChange={e => setFormData({ ...formData, created_at: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500" />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowAddModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">Cancel</button>
                <button type="submit"
                  className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">Add Expense</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Budgets ────────────────────────────────────────────────────────────────

function Budgets({ user }) {
  const [budgets, setBudgets]       = useState([]);
  const [categories, setCategories] = useState([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [formData, setFormData]     = useState({ category_id: '', amount: '', period: 'monthly', alert_threshold: '0.8' });

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [b, c] = await Promise.all([fetchBudgetStatus(), fetchCategories()]);
      setBudgets(b);
      setCategories(c);
    } catch (err) { console.error(err); }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await createBudget(formData.category_id ? parseInt(formData.category_id) : null,
        parseFloat(formData.amount), formData.period, parseFloat(formData.alert_threshold));
      setShowAddModal(false);
      setFormData({ category_id: '', amount: '', period: 'monthly', alert_threshold: '0.8' });
      loadData();
    } catch (err) { alert(err.message); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this budget?')) return;
    try { await deleteBudget(id); loadData(); } catch (err) { alert(err.message); }
  };

  const addNewCategory = async () => {
    const name = prompt('New category name:');
    if (!name?.trim()) return;
    try { await createCategory(name.trim()); const c = await fetchCategories(); setCategories(c); }
    catch (err) { alert(err.message); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Budgets</h1>
        <button onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition">
          <Target className="w-5 h-5" /><span>Set Budget</span>
        </button>
      </div>

      {budgets.length === 0 && (
        <div className="bg-white rounded-xl p-12 shadow-lg border border-gray-100 text-center text-gray-400">
          <Target className="w-16 h-16 mx-auto mb-4 text-gray-200" />
          <p className="text-lg font-medium">No budgets set yet</p>
          <p className="text-sm mt-2">Click "Set Budget" to create your first limit.</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {budgets.map(budget => {
          const pct = budget.budget_amount > 0 ? (budget.spent_amount / budget.budget_amount) * 100 : 0;
          return (
            <div key={budget.budget_id}
              className={`bg-white rounded-xl p-6 shadow-lg border-2 ${budget.is_over_budget ? 'border-red-300' : budget.should_alert ? 'border-yellow-300' : 'border-gray-100'}`}>
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">{budget.category_name || 'Overall Budget'}</h3>
                  <p className="text-sm text-gray-500 capitalize">{budget.period}</p>
                </div>
                <button onClick={() => handleDelete(budget.budget_id)} className="text-red-400 hover:text-red-700 transition">
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Spent</span>
                  <span className="font-semibold text-gray-900">${budget.spent_amount.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Limit</span>
                  <span className="font-semibold text-gray-900">${budget.budget_amount.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Remaining</span>
                  <span className={`font-semibold ${budget.remaining_amount < 0 ? 'text-red-600' : 'text-green-600'}`}>
                    ${Math.abs(budget.remaining_amount).toFixed(2)}{budget.remaining_amount < 0 && ' over'}
                  </span>
                </div>

                <div className="pt-2">
                  <div className="flex justify-between text-xs text-gray-500 mb-1">
                    <span>Progress</span><span>{Math.min(pct, 100).toFixed(0)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                    <div className={`h-full rounded-full transition-all ${budget.is_over_budget ? 'bg-red-500' : budget.should_alert ? 'bg-yellow-500' : 'bg-green-500'}`}
                      style={{ width: `${Math.min(pct, 100)}%` }} />
                  </div>
                </div>

                {budget.days_remaining != null && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Days left</span>
                    <span className="font-semibold text-gray-700">{budget.days_remaining}</span>
                  </div>
                )}

                {budget.is_over_budget && <div className="text-red-600 text-sm pt-1">⚠️ Over budget!</div>}
                {!budget.is_over_budget && budget.should_alert && <div className="text-yellow-600 text-sm pt-1">⚡ Approaching limit</div>}
              </div>
            </div>
          );
        })}
      </div>

      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Set New Budget</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Category (empty = overall)</label>
                <div className="flex gap-2">
                  <select value={formData.category_id} onChange={e => setFormData({ ...formData, category_id: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500">
                    <option value="">Overall Budget</option>
                    {categories.map(c => <option key={c.category_id} value={c.category_id}>{c.name}</option>)}
                  </select>
                  <button type="button" onClick={addNewCategory}
                    className="px-3 py-2 bg-indigo-100 text-indigo-700 rounded-lg hover:bg-indigo-200 font-medium text-sm whitespace-nowrap">
                    + New
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Amount ($)</label>
                <input type="number" step="0.01" value={formData.amount}
                  onChange={e => setFormData({ ...formData, amount: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Period</label>
                <select value={formData.period} onChange={e => setFormData({ ...formData, period: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500">
                  {['daily', 'weekly', 'monthly', 'yearly'].map(p => <option key={p} value={p} className="capitalize">{p}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Alert Threshold (0–1)</label>
                <input type="number" step="0.1" min="0" max="1" value={formData.alert_threshold}
                  onChange={e => setFormData({ ...formData, alert_threshold: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500" required />
                <p className="text-xs text-gray-400 mt-1">Alert when you reach this fraction (0.8 = 80%)</p>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowAddModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">Cancel</button>
                <button type="submit"
                  className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">Set Budget</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// ── AI Chat ────────────────────────────────────────────────────────────────

const SUGGESTED_QUERIES = [
  "What did I spend this month?",
  "Show category breakdown",
  "Check my budget status",
  "Detect unusual spending",
  "Forecast next 3 months",
  "Give me spending advice"
];

function AIDataCard({ data, categories, onExpenseCreated }) {
  const [confirmed, setConfirmed] = useState(false);

  if (!data) return null;

  // NL expense creation confirmation
  if (data.action === 'create_expense') {
    const cat = categories.find(c => c.name.toLowerCase() === data.suggested_category?.toLowerCase());
    const handleConfirm = async () => {
      if (!cat) { alert("Couldn't match category — please add the expense manually."); return; }
      try {
        await createExpense(cat.category_id, data.amount, data.description);
        setConfirmed(true);
        onExpenseCreated?.();
      } catch (err) { alert(err.message); }
    };
    if (confirmed) return <div className="mt-2 text-sm text-green-700 flex items-center gap-1"><Check className="w-4 h-4" /> Added!</div>;
    return (
      <div className="mt-3 bg-white border border-indigo-200 rounded-xl p-4 space-y-2">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Add this expense?</p>
        <p className="text-2xl font-bold text-indigo-600">${Number(data.amount).toFixed(2)}</p>
        <p className="text-sm text-gray-700">{data.description}</p>
        {data.suggested_category && <p className="text-xs text-gray-400">Category: {data.suggested_category}</p>}
        {!cat && <p className="text-xs text-red-500">⚠ No matching category found</p>}
        <div className="flex gap-2 pt-1">
          <button onClick={handleConfirm} disabled={!cat}
            className="px-4 py-1.5 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-40">
            Confirm
          </button>
        </div>
      </div>
    );
  }

  // Category breakdown bar chart
  if (data.by_category && Object.keys(data.by_category).length > 0) {
    const chartData = Object.entries(data.by_category).map(([name, value]) => ({ name, value }));
    return (
      <div className="mt-3 w-full">
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" tick={{ fontSize: 10 }} />
            <YAxis tickFormatter={v => `$${v}`} tick={{ fontSize: 10 }} />
            <Tooltip formatter={v => [`$${Number(v).toFixed(2)}`, 'Spent']} />
            <Bar dataKey="value" fill="#6366f1" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // Spending trend line chart
  if (data.trend && data.trend.length > 0) {
    return (
      <div className="mt-3 w-full">
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={data.trend}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" tick={{ fontSize: 10 }} />
            <YAxis tickFormatter={v => `$${v}`} tick={{ fontSize: 10 }} />
            <Tooltip formatter={v => [`$${Number(v).toFixed(2)}`, 'Spent']} />
            <Line type="monotone" dataKey="total_amount" stroke="#6366f1" strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // Forecast bar chart
  if (data.forecasts && data.forecasts.length > 0) {
    const chartData = data.forecasts.map((v, i) => ({ month: `+${i + 1}mo`, forecast: v }));
    return (
      <div className="mt-3 w-full">
        <p className="text-xs text-gray-500 mb-1">Forecast ({data.trend_direction}, {data.confidence_score?.toFixed(0)}% confidence)</p>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={chartData}>
            <XAxis dataKey="month" tick={{ fontSize: 10 }} />
            <YAxis tickFormatter={v => `$${v}`} tick={{ fontSize: 10 }} />
            <Tooltip formatter={v => [`$${Number(v).toFixed(2)}`, 'Forecast']} />
            <Bar dataKey="forecast" fill="#8b5cf6" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // Anomalies list
  if (data.anomalies && data.anomalies.length > 0) {
    return (
      <div className="mt-3 space-y-2">
        {data.anomalies.slice(0, 5).map((a, i) => (
          <div key={i} className={`px-3 py-2 rounded-lg text-xs ${a.severity === 'high' ? 'bg-red-50 border border-red-200 text-red-800' : 'bg-yellow-50 border border-yellow-200 text-yellow-800'}`}>
            <span className="font-semibold">${a.amount.toFixed(2)}</span> — {a.description}
            <span className="ml-1 text-gray-500">({a.deviation_percent > 0 ? '+' : ''}{a.deviation_percent}% vs avg)</span>
          </div>
        ))}
      </div>
    );
  }

  // Budget suggestions list
  if (data.suggestions && data.suggestions.length > 0) {
    return (
      <div className="mt-3 space-y-2">
        {data.suggestions.slice(0, 4).map((s, i) => (
          <div key={i} className={`px-3 py-2 rounded-lg text-xs border ${s.priority === 'high' ? 'bg-red-50 border-red-200' : s.priority === 'medium' ? 'bg-yellow-50 border-yellow-200' : 'bg-green-50 border-green-200'}`}>
            <div className="flex justify-between items-center mb-0.5">
              <span className="font-semibold">{s.category}</span>
              <span className={`px-1.5 py-0.5 rounded text-xs font-medium uppercase ${s.priority === 'high' ? 'bg-red-100 text-red-700' : s.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'}`}>{s.priority}</span>
            </div>
            {s.advice?.slice(0, 1).map((a, j) => <div key={j} className="text-gray-600">• {a}</div>)}
            {s.potential_monthly_savings > 0 && <div className="text-gray-500 mt-0.5">Potential savings: ${s.potential_monthly_savings.toFixed(2)}/mo</div>}
          </div>
        ))}
        {data.total_potential_savings > 0 && (
          <div className="text-xs font-semibold text-indigo-700 px-1">Total potential savings: ${data.total_potential_savings.toFixed(2)}/mo</div>
        )}
      </div>
    );
  }

  return null;
}

function AIChat({ user }) {
  const [messages, setMessages]         = useState([]);
  const [input, setInput]               = useState('');
  const [loading, setLoading]           = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [categories, setCategories]     = useState([]);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    Promise.all([loadChatHistory(user.user_id), fetchCategories()])
      .then(([history, cats]) => {
        setMessages(history.map(m => ({ sender: m.sender, message: m.message })));
        setCategories(cats);
      })
      .catch(() => {})
      .finally(() => setHistoryLoading(false));
  }, [user.user_id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const sendMessage = async (text) => {
    if (!text.trim()) return;
    const userMsg = { sender: 'User', message: text };
    const context = messages.slice(-8).map(m => `${m.sender}: ${m.message}`);
    setMessages(prev => [...prev, userMsg]);
    saveChatMessage(user.user_id, 'User', text);
    setInput('');
    setLoading(true);
    try {
      const res = await queryAI(text, context);
      const aiMsg = { sender: 'AI', message: res?.response || 'No response', data: res?.data };
      setMessages(prev => [...prev, aiMsg]);
      saveChatMessage(user.user_id, 'AI', res?.response || 'No response');
    } catch (err) {
      setMessages(prev => [...prev, { sender: 'AI', message: 'Sorry, I encountered an error. Please try again.' }]);
    } finally { setLoading(false); }
  };

  const handleSubmit = (e) => { e.preventDefault(); sendMessage(input); };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">AI Assistant</h1>
        <button onClick={() => { if (window.confirm('Clear chat?')) setMessages([]); }}
          className="flex items-center gap-2 px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition">
          <Trash2 className="w-4 h-4" /><span>Clear</span>
        </button>
      </div>

      {/* Suggested queries */}
      <div className="flex flex-wrap gap-2">
        {SUGGESTED_QUERIES.map(q => (
          <button key={q} onClick={() => sendMessage(q)}
            className="px-3 py-1.5 text-xs bg-indigo-50 text-indigo-700 rounded-full border border-indigo-200 hover:bg-indigo-100 transition">
            {q}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden flex flex-col" style={{ height: '580px' }}>
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {historyLoading && <div className="text-center text-gray-400 py-12">Loading chat history...</div>}
          {!historyLoading && messages.length === 0 && (
            <div className="text-center text-gray-400 py-16">
              <MessageCircle className="w-16 h-16 mx-auto mb-4 text-gray-200" />
              <p className="text-lg font-medium text-gray-500">Ask me anything about your spending!</p>
              <p className="text-sm mt-2">Try a suggested query above or type your own question.</p>
              <p className="text-xs mt-3 text-gray-400">Tip: say "I spent $30 on lunch" to log an expense directly.</p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.sender === 'User' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-xl p-4 ${msg.sender === 'User' ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-900'}`}>
                <p className="text-xs font-semibold mb-1 opacity-70">{msg.sender}</p>
                <p className="whitespace-pre-wrap text-sm">{msg.message}</p>
                {msg.sender === 'AI' && msg.data && (
                  <AIDataCard data={msg.data} categories={categories} onExpenseCreated={() => {}} />
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-xl p-4">
                <div className="flex space-x-1.5">
                  {[0, 0.2, 0.4].map((delay, i) => (
                    <div key={i} className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: `${delay}s` }} />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="border-t border-gray-200 p-4">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <input type="text" value={input} onChange={e => setInput(e.target.value)}
              placeholder="Ask about your spending, or say 'I spent $X on Y'..."
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm"
              disabled={loading} />
            <button type="submit" disabled={loading || !input.trim()}
              className="px-5 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition disabled:opacity-40 flex items-center gap-2">
              <Send className="w-4 h-4" /><span>Send</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
