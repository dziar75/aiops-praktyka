(function () {
  "use strict";

  const API = "/api";
  const STATUS_POLL_MS = 3000;
  const STATUS_LABELS = {
    pending: "Przyjęte",
    queued: "W kolejce",
    received: "Przyjęte",
    preparing: "W przygotowaniu",
    processing: "W przygotowaniu",
    ready: "Gotowe do odbioru",
    completed: "Wydane",
    done: "Wydane",
    failed: "Problem z zamówieniem",
    cancelled: "Anulowane",
  };

  const state = {
    menu: [],
    cart: new Map(), // menu_item_id -> { item, qty }
    pollTimer: null,
  };

  const el = (id) => document.getElementById(id);
  const money = new Intl.NumberFormat("pl-PL", { style: "currency", currency: "PLN" });

  function priceOf(item) {
    const p = item.price ?? item.price_pln ?? 0;
    return typeof p === "number" ? p : parseFloat(p) || 0;
  }

  function toast(message, isError) {
    const t = el("toast");
    t.textContent = message;
    t.classList.toggle("error", Boolean(isError));
    t.hidden = false;
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => { t.hidden = true; }, 3500);
  }

  async function api(path, options) {
    const resp = await fetch(API + path, {
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      ...options,
    });
    let body = null;
    try { body = await resp.json(); } catch (_) { /* empty body */ }
    if (!resp.ok) {
      const detail = body && (body.detail || body.error || body.message);
      throw new Error(typeof detail === "string" ? detail : `HTTP ${resp.status}`);
    }
    return body;
  }

  function normalizeItems(body) {
    if (Array.isArray(body)) return body;
    if (body && Array.isArray(body.items)) return body.items;
    if (body && Array.isArray(body.results)) return body.results;
    return [];
  }

  // ---- menu -----------------------------------------------------------
  function renderMenu(items, emptyText) {
    const list = el("menu-list");
    list.replaceChildren();
    el("menu-status").textContent = items.length ? "" : emptyText;
    el("menu-status").hidden = items.length > 0;

    for (const item of items) {
      const li = document.createElement("li");
      li.className = "menu-item";

      const info = document.createElement("div");
      const name = document.createElement("h3");
      name.textContent = item.name;
      info.appendChild(name);
      if (item.description || item.category) {
        const desc = document.createElement("p");
        desc.className = "muted";
        desc.textContent = [item.category, item.description].filter(Boolean).join(" · ");
        info.appendChild(desc);
      }

      const right = document.createElement("div");
      right.className = "menu-actions";
      const price = document.createElement("span");
      price.className = "price";
      price.textContent = money.format(priceOf(item));
      const add = document.createElement("button");
      add.type = "button";
      add.textContent = "Dodaj";
      const available = item.available !== false;
      add.disabled = !available;
      if (!available) add.textContent = "Brak";
      add.addEventListener("click", () => addToCart(item));
      right.append(price, add);

      li.append(info, right);
      list.appendChild(li);
    }
  }

  async function loadMenu() {
    el("menu-status").hidden = false;
    el("menu-status").textContent = "Ładowanie menu…";
    try {
      state.menu = normalizeItems(await api("/menu"));
      renderMenu(state.menu, "Menu na dziś nie jest jeszcze dostępne.");
    } catch (err) {
      el("menu-list").replaceChildren();
      el("menu-status").textContent = "Nie udało się pobrać menu. Spróbuj ponownie za chwilę.";
      console.error(err);
    }
  }

  async function search(query) {
    if (!query) { el("reset-search").hidden = true; return loadMenu(); }
    el("menu-status").hidden = false;
    el("menu-status").textContent = "Szukam…";
    try {
      const items = normalizeItems(await api("/menu/search?q=" + encodeURIComponent(query)));
      renderMenu(items, `Brak dań pasujących do „${query}”.`);
      el("reset-search").hidden = false;
    } catch (err) {
      el("menu-status").textContent = "Wyszukiwanie chwilowo niedostępne.";
      console.error(err);
    }
  }

  // ---- cart -----------------------------------------------------------
  function addToCart(item) {
    const entry = state.cart.get(item.id) || { item, qty: 0 };
    entry.qty = Math.min(entry.qty + 1, 5);
    state.cart.set(item.id, entry);
    renderCart();
  }

  function changeQty(id, delta) {
    const entry = state.cart.get(id);
    if (!entry) return;
    entry.qty += delta;
    if (entry.qty <= 0) state.cart.delete(id);
    renderCart();
  }

  function renderCart() {
    const list = el("cart-list");
    list.replaceChildren();
    let total = 0;
    for (const [id, { item, qty }] of state.cart) {
      total += priceOf(item) * qty;
      const li = document.createElement("li");
      const name = document.createElement("span");
      name.className = "cart-name";
      name.textContent = item.name;
      const controls = document.createElement("span");
      controls.className = "qty";
      const minus = document.createElement("button");
      minus.type = "button"; minus.textContent = "−"; minus.setAttribute("aria-label", "Mniej");
      minus.addEventListener("click", () => changeQty(id, -1));
      const count = document.createElement("span");
      count.textContent = qty;
      const plus = document.createElement("button");
      plus.type = "button"; plus.textContent = "+"; plus.setAttribute("aria-label", "Więcej");
      plus.disabled = qty >= 5;
      plus.addEventListener("click", () => changeQty(id, 1));
      controls.append(minus, count, plus);
      li.append(name, controls);
      list.appendChild(li);
    }
    el("cart-empty").hidden = state.cart.size > 0;
    el("cart-total").textContent = money.format(total);
    el("order-button").disabled = state.cart.size === 0;
  }

  async function placeOrder() {
    const button = el("order-button");
    const employeeId = parseInt(el("employee-id").value, 10) || 1;
    const payload = {
      employee_id: `e-${employeeId}`,
      items: [...state.cart.values()].map(({ item, qty }) => ({ menu_item_id: item.id, qty })),
    };
    button.disabled = true;
    button.textContent = "Wysyłanie…";
    try {
      const order = await api("/orders", { method: "POST", body: JSON.stringify(payload) });
      const orderId = order.order_id ?? order.id;
      state.cart.clear();
      renderCart();
      toast(`Zamówienie nr ${orderId} przyjęte.`);
      el("status-input").value = orderId;
      trackOrder(orderId);
    } catch (err) {
      toast("Nie udało się złożyć zamówienia: " + err.message, true);
      button.disabled = state.cart.size === 0;
    } finally {
      button.textContent = "Zamów";
    }
  }

  // ---- order status ---------------------------------------------------
  function renderStatus(order) {
    const box = el("order-status");
    box.classList.remove("muted");
    box.replaceChildren();
    const id = order.order_id ?? order.id;
    const status = String(order.status || "pending").toLowerCase();

    const head = document.createElement("div");
    head.className = "status-head";
    const title = document.createElement("strong");
    title.textContent = `Zamówienie nr ${id}`;
    const badge = document.createElement("span");
    badge.className = `badge badge-${status}`;
    badge.textContent = STATUS_LABELS[status] || status;
    head.append(title, badge);
    box.appendChild(head);

    if (Array.isArray(order.items) && order.items.length) {
      const ul = document.createElement("ul");
      ul.className = "status-items";
      for (const it of order.items) {
        const li = document.createElement("li");
        const name = it.name || `Pozycja #${it.menu_item_id}`;
        li.textContent = `${it.qty ?? 1} × ${name}`;
        ul.appendChild(li);
      }
      box.appendChild(ul);
    }
    if (order.total != null) {
      const p = document.createElement("p");
      p.textContent = "Do zapłaty: " + money.format(Number(order.total));
      box.appendChild(p);
    }
    return status;
  }

  async function fetchStatus(orderId) {
    try {
      const order = await api("/orders/" + encodeURIComponent(orderId));
      const status = renderStatus(order);
      return !["ready", "completed", "done", "failed", "cancelled"].includes(status);
    } catch (err) {
      const box = el("order-status");
      box.classList.add("muted");
      box.textContent = `Nie znaleziono zamówienia nr ${orderId} (${err.message}).`;
      return false;
    }
  }

  function trackOrder(orderId) {
    clearTimeout(state.pollTimer);
    const tick = async () => {
      const keepPolling = await fetchStatus(orderId);
      if (keepPolling) state.pollTimer = setTimeout(tick, STATUS_POLL_MS);
    };
    tick();
  }

  // ---- wiring ---------------------------------------------------------
  document.addEventListener("DOMContentLoaded", () => {
    el("search-form").addEventListener("submit", (e) => {
      e.preventDefault();
      search(el("search-input").value.trim());
    });
    el("reset-search").addEventListener("click", () => {
      el("search-input").value = "";
      el("reset-search").hidden = true;
      renderMenu(state.menu, "Menu na dziś nie jest jeszcze dostępne.");
    });
    el("order-button").addEventListener("click", placeOrder);
    el("status-form").addEventListener("submit", (e) => {
      e.preventDefault();
      const id = el("status-input").value.trim();
      if (id) trackOrder(id);
    });
    renderCart();
    loadMenu();
  });
})();
