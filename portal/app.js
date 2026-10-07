(() => {
  const API = "/api";
  const state = {
    token: localStorage.getItem("asist_token") || "",
    me: null,
    currentId: null,
    categorias: [],
  };

  const $ = (id) => document.getElementById(id);
  const views = ["login", "incidencias", "detalle", "nueva", "equipos"];

  function show(view) {
    views.forEach((v) => {
      const el = $(`view-${v}`);
      if (el) el.classList.toggle("hidden", v !== view);
    });
    $("nav").classList.toggle("hidden", view === "login");
  }

  async function api(path, opts = {}) {
    const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
    if (state.token) headers.Authorization = `Bearer ${state.token}`;
    const res = await fetch(`${API}${path}`, { ...opts, headers });
    const text = await res.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { detail: text };
    }
    if (!res.ok) {
      const msg = data?.detail || res.statusText;
      throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
    return data;
  }

  async function afterLogin() {
    state.me = await api("/me");
    state.categorias = await api("/categorias");
    fillCategorias();
    show("incidencias");
    await loadIncidencias();
  }

  function fillCategorias() {
    const sel = $("nueva-categoria");
    sel.innerHTML = "";
    state.categorias.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.value;
      opt.textContent = c.value;
      opt.dataset.titulo = c.titulo;
      opt.dataset.desc = c.descripcion;
      sel.appendChild(opt);
    });
    applyPlantilla();
  }

  function applyPlantilla() {
    const opt = $("nueva-categoria").selectedOptions[0];
    if (!opt) return;
    $("nueva-titulo").value = opt.dataset.titulo || "";
    $("nueva-desc").value = opt.dataset.desc || "";
  }

  async function loadIncidencias() {
    const items = await api("/incidencias");
    const box = $("lista-incidencias");
    box.innerHTML = "";
    if (!items.length) {
      box.innerHTML = "<p class='muted'>No hay incidencias. Crea la primera.</p>";
      return;
    }
    items.forEach((inc) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "item" + (inc.vencida ? " vencida" : "");
      btn.innerHTML = `
        <strong>${inc.codigo}</strong> ${inc.titulo}
        <div class="meta">
          <span class="badge">${inc.estado_usuario}</span>
          <span class="badge">${inc.categoria}</span>
          <span class="badge">${inc.prioridad}</span>
          ${inc.vencida ? '<span class="badge warn">Vencida</span>' : ""}
        </div>`;
      btn.onclick = () => openDetalle(inc.id);
      box.appendChild(btn);
    });
  }

  async function openDetalle(id) {
    state.currentId = id;
    const inc = await api(`/incidencias/${id}`);
    show("detalle");
    $("detalle").innerHTML = `
      <h1>${inc.codigo} — ${inc.titulo}</h1>
      <div class="meta">
        <span class="badge">${inc.estado_usuario}</span>
        <span class="badge">${inc.categoria}</span>
        ${inc.vencida ? '<span class="badge warn">Vencida</span>' : ""}
        · SLA: ${inc.fecha_limite || "—"}
        · Técnico: ${inc.tecnico_nombre || "Sin asignar"}
      </div>
      <p>${(inc.descripcion || "").replace(/</g, "&lt;")}</p>`;
    const com = $("detalle-comentarios");
    com.innerHTML = "";
    (inc.comentarios || []).forEach((c) => {
      const d = document.createElement("div");
      d.className = "item";
      d.style.cursor = "default";
      d.textContent = `${(c.fecha || "").slice(0, 16)} · ${c.usuario_nombre || ""}: ${c.texto}`;
      com.appendChild(d);
    });
    if (!(inc.comentarios || []).length) {
      com.innerHTML = "<p class='muted'>Sin comentarios</p>";
    }
    const acciones = $("detalle-acciones");
    acciones.innerHTML = "";
    if (["Pendiente", "En reparación"].includes(inc.estado)) {
      const b = document.createElement("button");
      b.className = "primary";
      b.textContent = "Confirmar resolución";
      b.onclick = async () => {
        await api(`/incidencias/${id}/confirmar`, { method: "POST", body: "{}" });
        openDetalle(id);
      };
      acciones.appendChild(b);
    }
    if (inc.estado === "Cerrada") {
      const b = document.createElement("button");
      b.className = "ghost";
      b.textContent = "Reabrir";
      b.onclick = async () => {
        await api(`/incidencias/${id}/reabrir`, { method: "POST", body: "{}" });
        openDetalle(id);
      };
      acciones.appendChild(b);
    }
  }

  async function loadEquiposSelect() {
    const eqs = await api("/equipos");
    const sel = $("nueva-equipo");
    sel.innerHTML = "";
    eqs.forEach((e) => {
      const opt = document.createElement("option");
      opt.value = e.id;
      opt.textContent = `${e.nombre_completo} (${e.numero_serie})`;
      sel.appendChild(opt);
    });
    return eqs;
  }

  async function loadEquipos() {
    const eqs = await api("/equipos");
    const box = $("lista-equipos");
    box.innerHTML = "";
    eqs.forEach((e) => {
      const d = document.createElement("div");
      d.className = "item";
      d.style.cursor = "default";
      d.innerHTML = `<strong>${e.nombre_completo}</strong><div class="meta">S/N ${e.numero_serie} · ${e.sistema_operativo || ""}</div>`;
      box.appendChild(d);
    });
    if (!eqs.length) box.innerHTML = "<p class='muted'>Sin equipos registrados.</p>";
  }

  $("btn-login").onclick = async () => {
    $("login-error").textContent = "";
    try {
      const data = await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: $("login-email").value.trim(),
          password: $("login-pass").value,
        }),
      });
      state.token = data.access_token;
      localStorage.setItem("asist_token", state.token);
      await afterLogin();
    } catch (err) {
      $("login-error").textContent = err.message;
    }
  };

  $("btn-logout").onclick = () => {
    state.token = "";
    localStorage.removeItem("asist_token");
    show("login");
  };

  document.querySelectorAll("#nav button[data-view]").forEach((btn) => {
    btn.onclick = async () => {
      const v = btn.dataset.view;
      show(v);
      if (v === "incidencias") await loadIncidencias();
      if (v === "nueva") {
        await loadEquiposSelect();
        fillCategorias();
      }
      if (v === "equipos") await loadEquipos();
    };
  });

  $("btn-volver").onclick = async () => {
    show("incidencias");
    await loadIncidencias();
  };

  $("nueva-categoria").onchange = applyPlantilla;

  $("btn-crear").onclick = async () => {
    $("nueva-error").textContent = "";
    try {
      const creada = await api("/incidencias", {
        method: "POST",
        body: JSON.stringify({
          equipo_id: Number($("nueva-equipo").value),
          titulo: $("nueva-titulo").value.trim(),
          descripcion: $("nueva-desc").value.trim(),
          prioridad: $("nueva-prio").value,
          categoria: $("nueva-categoria").value,
        }),
      });
      await openDetalle(creada.id);
    } catch (err) {
      $("nueva-error").textContent = err.message;
    }
  };

  $("btn-comentar").onclick = async () => {
    if (!state.currentId) return;
    const texto = $("comentario-texto").value.trim();
    if (!texto) return;
    await api(`/incidencias/${state.currentId}/comentarios`, {
      method: "POST",
      body: JSON.stringify({ texto }),
    });
    $("comentario-texto").value = "";
    await openDetalle(state.currentId);
  };

  $("btn-eq").onclick = async () => {
    $("eq-error").textContent = "";
    try {
      await api("/equipos", {
        method: "POST",
        body: JSON.stringify({
          numero_serie: $("eq-serie").value.trim(),
          marca: $("eq-marca").value.trim(),
          modelo: $("eq-modelo").value.trim(),
          sistema_operativo: $("eq-so").value.trim(),
        }),
      });
      $("eq-serie").value = "";
      $("eq-marca").value = "";
      $("eq-modelo").value = "";
      $("eq-so").value = "";
      await loadEquipos();
    } catch (err) {
      $("eq-error").textContent = err.message;
    }
  };

  if (state.token) {
    afterLogin().catch(() => {
      state.token = "";
      localStorage.removeItem("asist_token");
      show("login");
    });
  } else {
    show("login");
  }
})();
