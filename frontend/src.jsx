import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  BarChart3,
  Boxes,
  CheckCircle2,
  Database,
  Edit3,
  Package,
  Plus,
  RefreshCw,
  ShoppingCart,
  Trash2,
  Users,
  X,
  Zap,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./style.css";

const API = "https://ecommerce-data-engineering-platform.onrender.com";

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  let data = {};
  try {
    data = await response.json();
  } catch {
    data = {};
  }
  if (!response.ok) throw new Error(data.detail || "Request failed");
  return data;
}

const money = (value) => `₹${Number(value || 0).toLocaleString("en-IN")}`;

function dateTime(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString("en-IN", {
    day: "numeric",
    month: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function statusClass(value) {
  return `status ${String(value || "").toLowerCase()}`;
}

function App() {
  const [page, setPage] = useState("Overview");
  const [overview, setOverview] = useState(null);
  const [revenue, setRevenue] = useState([]);
  const [topProducts, setTopProducts] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadDashboard = async () => {
    const [a, b, c, d] = await Promise.all([
      api("/analytics/overview"),
      api("/analytics/revenue"),
      api("/analytics/top-products"),
      api("/pipeline/runs"),
    ]);
    setOverview(a);
    setRevenue(b);
    setTopProducts(c);
    setRuns(d);
  };

  useEffect(() => {
    loadDashboard()
      .catch((error) => console.error(error))
      .finally(() => setLoading(false));
  }, []);

  const refresh = async () => {
    setRefreshing(true);
    try {
      await loadDashboard();
    } catch (error) {
      alert(error.message);
    } finally {
      setRefreshing(false);
    }
  };

  const changed = async () => {
    await loadDashboard();
  };

  if (loading || !overview) {
    return <div className="loading">Loading DataFlow…</div>;
  }

  return (
    <div className="app">
      <Sidebar page={page} setPage={setPage} />
      <main>
        {page === "Overview" && (
          <OverviewPage
            overview={overview}
            revenue={revenue}
            topProducts={topProducts}
            runs={runs}
            refresh={refresh}
            refreshing={refreshing}
          />
        )}
        {page === "Orders" && <OrdersPage onChanged={changed} />}
        {page === "Customers" && <CustomersPage onChanged={changed} />}
        {page === "Products" && <ProductsPage onChanged={changed} />}
        {page === "Analytics" && (
          <AnalyticsPage
            overview={overview}
            revenue={revenue}
            topProducts={topProducts}
            refresh={refresh}
            refreshing={refreshing}
          />
        )}
        {page === "Pipeline Health" && (
          <PipelinePage
            runs={runs}
            refresh={refresh}
            refreshing={refreshing}
          />
        )}
      </main>
    </div>
  );
}

function Sidebar({ page, setPage }) {
  const items = [
    ["Overview", <BarChart3 />],
    ["Orders", <ShoppingCart />],
    ["Customers", <Users />],
    ["Products", <Boxes />],
    ["Analytics", <BarChart3 />],
    ["Pipeline Health", <Activity />],
  ];

  return (
    <aside>
      <div className="brand">
        <Activity />
        <span>DataFlow</span>
      </div>
      <nav>
        {items.map(([label, icon]) => (
          <button
            key={label}
            className={page === label ? "nav-item active" : "nav-item"}
            onClick={() => setPage(label)}
          >
            {React.cloneElement(icon, { size: 18 })}
            <span>{label}</span>
          </button>
        ))}
      </nav>
      <div className="sidefoot">
        E-Commerce Data Platform
        <br />
        <small>v1.0 • Live pipeline</small>
      </div>
    </aside>
  );
}

function Header({ title, description, action }) {
  return (
    <header>
      <div>
        <p className="eyebrow">DATA OPERATIONS</p>
        <h1>{title}</h1>
        <p className="muted">{description}</p>
      </div>
      {action}
    </header>
  );
}

function HeaderButtons({ onRefresh, refreshing, children }) {
  return (
    <div className="header-actions">
      <button onClick={onRefresh} disabled={refreshing}>
        <RefreshCw size={16} className={refreshing ? "spin" : ""} />
        Refresh
      </button>
      {children}
    </div>
  );
}

function StatCard({ icon, label, value }) {
  return (
    <div className="card">
      <div className="icon">{icon}</div>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

function Panel({ title, children, action }) {
  return (
    <section className="panel">
      <div className="panelhead">
        <h2>{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

function OverviewPage({ overview, revenue, topProducts, runs, refresh, refreshing }) {
  return (
    <>
      <Header
        title="Analytics Overview"
        description="Monitor revenue, orders and pipeline health in one place."
        action={
          <button onClick={refresh} disabled={refreshing}>
            <RefreshCw size={16} className={refreshing ? "spin" : ""} />
            Refresh
          </button>
        }
      />
      <section className="cards">
        <StatCard icon={<ShoppingCart />} label="Total Orders" value={overview.orders} />
        <StatCard icon={<Database />} label="Total Revenue" value={money(overview.revenue)} />
        <StatCard icon={<Users />} label="Customers" value={overview.customers} />
        <StatCard icon={<Boxes />} label="Products" value={overview.products} />
      </section>
      <section className="grid">
        <Panel title="Revenue Trend"><RevenueChart data={revenue} /></Panel>
        <Panel title="Top Products"><TopProductsChart data={topProducts} /></Panel>
      </section>
      <PipelineActivity runs={runs} />
    </>
  );
}

function OrdersPage({ onChanged }) {
  const [orders, setOrders] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({
    customer_id: "",
    product_id: "",
    quantity: 1,
    status: "processing",
  });

  const load = async () => {
    try {
      const [o, c, p] = await Promise.all([
        api("/orders"),
        api("/customers"),
        api("/products"),
      ]);
      setOrders(o);
      setCustomers(c);
      setProducts(p);
    } catch (error) {
      alert(error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const selectedProduct = products.find(
    (p) => String(p.product_id) === String(form.product_id)
  );
  const total = Number(selectedProduct?.price || 0) * Number(form.quantity || 0);

  const openCreate = () => {
    setEditing(null);
    setForm({ customer_id: "", product_id: "", quantity: 1, status: "processing" });
    setModal(true);
  };

  const openEdit = (order) => {
    setEditing(order);
    setForm({
      customer_id: String(order.customer_id || ""),
      product_id: String(order.product_id || ""),
      quantity: order.quantity || 1,
      status: order.status || "processing",
    });
    setModal(true);
  };

  const save = async (event) => {
    event.preventDefault();
    if (!form.customer_id || !form.product_id) {
      alert("Please select customer and product");
      return;
    }
    if (Number(form.quantity) <= 0) {
      alert("Quantity must be greater than 0");
      return;
    }
    setSaving(true);
    try {
      const body = JSON.stringify({
        customer_id: Number(form.customer_id),
        product_id: Number(form.product_id),
        quantity: Number(form.quantity),
        status: form.status,
      });
      await api(editing ? `/orders/${editing.order_id}` : "/orders", {
        method: editing ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body,
      });
      setModal(false);
      await load();
      await onChanged();
    } catch (error) {
      alert(error.message);
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id) => {
    if (!window.confirm(`Delete order #${id}?`)) return;
    try {
      await api(`/orders/${id}`, { method: "DELETE" });
      await load();
      await onChanged();
    } catch (error) {
      alert(error.message);
    }
  };

  return (
    <>
      <Header
        title="Orders"
        description="View and monitor all processed customer orders."
        action={
          <HeaderButtons onRefresh={load} refreshing={false}>
            <button className="primary-button" onClick={openCreate}>
              <Plus size={16} />
              Create Order
            </button>
          </HeaderButtons>
        }
      />

      <Panel
        title="Order Records"
        action={<ShoppingCart size={23} />}
      >
        <p className="muted table-count">{orders.length} orders loaded</p>
        {loading ? (
          <div className="empty-state">Loading orders…</div>
        ) : (
          <div className="table">
            <div className="order-row order-header">
              <span>ORDER ID</span>
              <span>CUSTOMER</span>
              <span>DATE</span>
              <span>STATUS</span>
              <span>AMOUNT</span>
              <span>ACTIONS</span>
            </div>
            {orders.map((order) => (
              <div className="order-row" key={order.order_id}>
                <span>#{order.order_id}</span>
                <span className="customer-cell">
                  <strong>{order.customer_name}</strong>
                  <small>ID: {order.customer_id}</small>
                </span>
                <span>{dateTime(order.order_date)}</span>
                <span><b className={statusClass(order.status)}>{order.status}</b></span>
                <strong>{money(order.total_amount)}</strong>
                <span className="row-actions">
                  <button className="icon-action edit" onClick={() => openEdit(order)} title="Edit">
                    <Edit3 size={15} />
                  </button>
                  <button className="icon-action delete" onClick={() => remove(order.order_id)} title="Delete">
                    <Trash2 size={15} />
                  </button>
                </span>
              </div>
            ))}
          </div>
        )}
      </Panel>

      {modal && (
        <OrderModal
          editing={editing}
          form={form}
          setForm={setForm}
          customers={customers}
          products={products}
          total={total}
          saving={saving}
          onClose={() => setModal(false)}
          onSubmit={save}
        />
      )}
    </>
  );
}

function OrderModal({ editing, form, setForm, customers, products, total, saving, onClose, onSubmit }) {
  return (
    <div className="modal-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <div>
            <h2>{editing ? "Edit Order" : "Create Order"}</h2>
            <p className="muted">{editing ? "Update order details" : "Add a new customer order"}</p>
          </div>
          <button className="modal-close" onClick={onClose}><X size={18} /></button>
        </div>
        <form onSubmit={onSubmit}>
          <div className="form-grid">
            <Field label="Customer">
              <select value={form.customer_id} onChange={(e) => setForm({ ...form, customer_id: e.target.value })}>
                <option value="">Select customer</option>
                {customers.map((c) => <option key={c.customer_id} value={c.customer_id}>{c.name}</option>)}
              </select>
            </Field>
            <Field label="Product">
              <select value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })}>
                <option value="">Select product</option>
                {products.map((p) => <option key={p.product_id} value={p.product_id}>{p.name} — {money(p.price)}</option>)}
              </select>
            </Field>
            <Field label="Quantity">
              <input type="number" min="1" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })} />
            </Field>
            <Field label="Status">
              <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                <option value="processing">Processing</option>
                <option value="shipped">Shipped</option>
                <option value="delivered">Delivered</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </Field>
          </div>
          <div className="total-preview">
            <span>Total Amount</span>
            <strong>{money(total)}</strong>
          </div>
          <div className="modal-footer">
            <button type="button" onClick={onClose}>Cancel</button>
            <button type="submit" className="primary-button" disabled={saving}>
              {saving ? "Saving…" : editing ? "Update Order" : "Create Order"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function CustomersPage({ onChanged }) {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", city: "" });

  const load = async () => {
    try { setCustomers(await api("/customers")); }
    catch (error) { alert(error.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const create = () => {
    setEditing(null);
    setForm({ name: "", email: "", city: "" });
    setModal(true);
  };

  const edit = (customer) => {
    setEditing(customer);
    setForm({ name: customer.name, email: customer.email, city: customer.city || "" });
    setModal(true);
  };

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api(editing ? `/customers/${editing.customer_id}` : "/customers", {
        method: editing ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      setModal(false);
      await load();
      await onChanged();
    } catch (error) { alert(error.message); }
    finally { setSaving(false); }
  };

  const remove = async (id) => {
    if (!window.confirm("Delete this customer?")) return;
    try {
      await api(`/customers/${id}`, { method: "DELETE" });
      await load();
      await onChanged();
    } catch (error) { alert(error.message); }
  };

  return (
    <>
      <Header
        title="Customers"
        description="Manage customer records and account information."
        action={
          <HeaderButtons onRefresh={load} refreshing={false}>
            <button className="primary-button" onClick={create}><Plus size={16} />Add Customer</button>
          </HeaderButtons>
        }
      />
      <Panel title="Customer Records" action={<Users size={23} />}>
        <p className="muted table-count">{customers.length} customers loaded</p>
        {loading ? <div className="empty-state">Loading customers…</div> : (
          <div className="table">
            <div className="customer-row customer-header"><span>ID</span><span>NAME</span><span>EMAIL</span><span>CITY</span><span>ACTIONS</span></div>
            {customers.map((c) => (
              <div className="customer-row" key={c.customer_id}>
                <span>#{c.customer_id}</span>
                <strong>{c.name}</strong>
                <span>{c.email}</span>
                <span>{c.city || "-"}</span>
                <span className="row-actions">
                  <button className="icon-action edit" onClick={() => edit(c)}><Edit3 size={15} /></button>
                  <button className="icon-action delete" onClick={() => remove(c.customer_id)}><Trash2 size={15} /></button>
                </span>
              </div>
            ))}
          </div>
        )}
      </Panel>
      {modal && (
        <SimpleModal title={editing ? "Edit Customer" : "Create Customer"} subtitle="Add customer information" onClose={() => setModal(false)}>
          <form onSubmit={save}>
            <Field label="Name"><input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Customer name" /></Field>
            <Field label="Email"><input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="customer@email.com" /></Field>
            <Field label="City"><input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} placeholder="City" /></Field>
            <ModalFooter saving={saving} label={editing ? "Update Customer" : "Create Customer"} onClose={() => setModal(false)} />
          </form>
        </SimpleModal>
      )}
    </>
  );
}

function ProductsPage({ onChanged }) {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ name: "", category: "", price: "" });

  const load = async () => {
    try { setProducts(await api("/products")); }
    catch (error) { alert(error.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const create = () => {
    setEditing(null);
    setForm({ name: "", category: "", price: "" });
    setModal(true);
  };

  const edit = (p) => {
    setEditing(p);
    setForm({ name: p.name, category: p.category, price: p.price });
    setModal(true);
  };

  const save = async (e) => {
    e.preventDefault();
    if (Number(form.price) < 0) return alert("Price cannot be negative");
    setSaving(true);
    try {
      await api(editing ? `/products/${editing.product_id}` : "/products", {
        method: editing ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: form.name, category: form.category, price: Number(form.price) }),
      });
      setModal(false);
      await load();
      await onChanged();
    } catch (error) { alert(error.message); }
    finally { setSaving(false); }
  };

  const remove = async (id) => {
    if (!window.confirm("Delete this product?")) return;
    try {
      await api(`/products/${id}`, { method: "DELETE" });
      await load();
      await onChanged();
    } catch (error) { alert(error.message); }
  };

  return (
    <>
      <Header
        title="Products"
        description="Manage products, categories and pricing."
        action={
          <HeaderButtons onRefresh={load} refreshing={false}>
            <button className="primary-button" onClick={create}><Plus size={16} />Add Product</button>
          </HeaderButtons>
        }
      />
      <Panel title="Product Records" action={<Package size={23} />}>
        <p className="muted table-count">{products.length} products loaded</p>
        {loading ? <div className="empty-state">Loading products…</div> : (
          <div className="table">
            <div className="product-row product-header"><span>ID</span><span>PRODUCT</span><span>CATEGORY</span><span>PRICE</span><span>ACTIONS</span></div>
            {products.map((p) => (
              <div className="product-row" key={p.product_id}>
                <span>#{p.product_id}</span>
                <strong>{p.name}</strong>
                <span>{p.category}</span>
                <strong>{money(p.price)}</strong>
                <span className="row-actions">
                  <button className="icon-action edit" onClick={() => edit(p)}><Edit3 size={15} /></button>
                  <button className="icon-action delete" onClick={() => remove(p.product_id)}><Trash2 size={15} /></button>
                </span>
              </div>
            ))}
          </div>
        )}
      </Panel>
      {modal && (
        <SimpleModal title={editing ? "Edit Product" : "Create Product"} subtitle="Add product information" onClose={() => setModal(false)}>
          <form onSubmit={save}>
            <Field label="Product Name"><input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Product name" /></Field>
            <Field label="Category"><input required value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder="Category" /></Field>
            <Field label="Price"><input required type="number" min="0" step="0.01" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} placeholder="0.00" /></Field>
            <ModalFooter saving={saving} label={editing ? "Update Product" : "Create Product"} onClose={() => setModal(false)} />
          </form>
        </SimpleModal>
      )}
    </>
  );
}

function Field({ label, children }) {
  return <div className="form-group"><label>{label}</label>{children}</div>;
}

function SimpleModal({ title, subtitle, onClose, children }) {
  return (
    <div className="modal-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <div><h2>{title}</h2><p className="muted">{subtitle}</p></div>
          <button className="modal-close" onClick={onClose}><X size={18} /></button>
        </div>
        <div className="modal-form">{children}</div>
      </div>
    </div>
  );
}

function ModalFooter({ saving, label, onClose }) {
  return (
    <div className="modal-footer">
      <button type="button" onClick={onClose}>Cancel</button>
      <button type="submit" className="primary-button" disabled={saving}>{saving ? "Saving…" : label}</button>
    </div>
  );
}

function AnalyticsPage({ overview, revenue, topProducts, refresh, refreshing }) {
  return (
    <>
      <Header title="Analytics" description="Explore live revenue and product performance." action={<button onClick={refresh} disabled={refreshing}><RefreshCw size={16} className={refreshing ? "spin" : ""} />Refresh</button>} />
      <section className="cards">
        <StatCard icon={<ShoppingCart />} label="Orders" value={overview.orders} />
        <StatCard icon={<Database />} label="Revenue" value={money(overview.revenue)} />
        <StatCard icon={<Users />} label="Customers" value={overview.customers} />
        <StatCard icon={<Package />} label="Products" value={overview.products} />
      </section>
      <section className="grid">
        <Panel title="Revenue Trend"><RevenueChart data={revenue} large /></Panel>
        <Panel title="Top Products"><TopProductsChart data={topProducts} /></Panel>
      </section>
      <Panel title="Order Status">
        <p className="muted table-count">Current order lifecycle</p>
        <div className="status-grid">
          <StatusCard label="Processing" value={overview.processing} />
          <StatusCard label="Shipped" value={overview.shipped} />
          <StatusCard label="Delivered" value={overview.delivered} />
          <StatusCard label="Cancelled" value={overview.cancelled} />
        </div>
      </Panel>
    </>
  );
}

function PipelinePage({ runs, refresh, refreshing }) {
  return (
    <>
      <Header title="Pipeline Health" description="Monitor ETL processing and pipeline activity." action={<button onClick={refresh} disabled={refreshing}><RefreshCw size={16} className={refreshing ? "spin" : ""} />Refresh</button>} />
      <section className="cards">
        <StatCard icon={<Activity />} label="Pipeline Runs" value={runs.length} />
        <StatCard icon={<CheckCircle2 />} label="Latest Status" value={runs[0]?.status || "Unknown"} />
        <StatCard icon={<Database />} label="Records Processed" value={runs[0]?.records || 0} />
        <StatCard icon={<Zap />} label="Pipeline" value={runs[0]?.pipeline || "-"} />
      </section>
      <PipelineActivity runs={runs} full />
    </>
  );
}

function PipelineActivity({ runs, full = false }) {
  const data = full ? runs : runs.slice(0, 5);
  return (
    <Panel title="Pipeline Activity" action={<span className="live"><i />LIVE</span>}>
      <p className="muted table-count">Recent ETL processing runs</p>
      <div className="table">
        <div className="pipeline-row pipeline-header"><span>PIPELINE</span><span>STATUS</span><span>RECORDS</span><span>STARTED</span></div>
        {data.map((run) => (
          <div className="pipeline-row" key={run.run_id}>
            <span>{run.pipeline}</span>
            <span><b className={run.status === "success" ? "ok" : "warn"}>{run.status}</b></span>
            <span>{run.records}</span>
            <span>{dateTime(run.started_at)}</span>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function StatusCard({ label, value }) {
  return <div className="status-card"><span>{label}</span><strong>{value}</strong></div>;
}

function RevenueChart({ data, large = false }) {
  return (
    <ResponsiveContainer width="100%" height={large ? 350 : 260}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="day" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip formatter={(value) => money(value)} />
        <Line type="monotone" dataKey="revenue" strokeWidth={3} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}

function TopProductsChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data.slice(0, 5)}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="product_name" hide />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip formatter={(value) => money(value)} />
        <Bar dataKey="revenue" radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode><App /></React.StrictMode>
);
