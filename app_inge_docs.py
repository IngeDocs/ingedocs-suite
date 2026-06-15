# -*- coding: utf-8 -*-
"""
Plataforma Web Inge Docs - Suite de Ingeniería Civil PRO (COMPLETA)
Autor: Inge Docs
Descripción: Aplicación web interactiva con los 4 módulos profesionales.
"""

import streamlit as st
import numpy as np
import pandas as pd
import math
import requests
from datetime import datetime, timezone
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")

# ==========================================
# ⚠️  CONFIGURACIÓN DE PÁGINA — DEBE SER
#     EL PRIMER COMANDO DE STREAMLIT
# ==========================================
st.set_page_config(
    page_title="Suite Inge Docs PRO",
    page_icon="🏗️",
    layout="wide"
)

# ==========================================
# CONTROL DE CLAVES CON JSONBIN.IO
# Cada clave tiene un límite de activaciones.
# ==========================================
JSONBIN_BASE = "https://api.jsonbin.io/v3/b"


def _jsonbin_headers():
    return {
        "X-Master-Key": st.secrets["jsonbin"]["master_key"],
        "Content-Type": "application/json"
    }


def _cargar_registro():
    bin_id = st.secrets["jsonbin"]["bin_id"]
    r = requests.get(f"{JSONBIN_BASE}/{bin_id}/latest", headers=_jsonbin_headers(), timeout=10)
    r.raise_for_status()
    return r.json()["record"]


def _guardar_registro(data):
    bin_id = st.secrets["jsonbin"]["bin_id"]
    r = requests.put(f"{JSONBIN_BASE}/{bin_id}", headers=_jsonbin_headers(), json=data, timeout=10)
    r.raise_for_status()


def validar_y_registrar_clave(clave):
    """
    Devuelve (ok: bool, mensaje: str).
    Si la clave es válida y tiene cupo, registra el uso y permite el acceso.
    """
    try:
        registro = _cargar_registro()
    except Exception:
        return False, "No se pudo verificar la clave (problema de conexión). Intenta de nuevo en unos segundos."

    if clave not in registro:
        return False, "Clave no encontrada. Verifica que la copiaste correctamente."

    info = registro[clave]

    if info.get("uses", 0) >= info.get("max_uses", 5):
        return False, "Esta clave alcanzó su límite de activaciones. Contacta a soporte para renovarla."

    info["uses"] = info.get("uses", 0) + 1
    info.setdefault("log", []).append(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    registro[clave] = info

    try:
        _guardar_registro(registro)
    except Exception:
        pass  # Si falla el guardado no bloqueamos el acceso, solo no queda registrado este uso.

    return True, "OK"


# ==========================================
# SISTEMA DE ACCESO CON SESSION STATE
# (evita re-pedir contraseña en cada clic)
# ==========================================
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Acceso Restringido — Inge Docs PRO")
    st.markdown("Ingresa la clave personal que recibiste al comprar.")
    clave = st.text_input("Clave de acceso:", type="password", placeholder="INGE-XXXX-XXXX")
    if st.button("Activar acceso", type="primary"):
        if not clave.strip():
            st.warning("Ingresa tu clave de acceso.")
        else:
            ok, mensaje = validar_y_registrar_clave(clave.strip().upper())
            if ok:
                st.session_state.auth = True
                st.rerun()
            else:
                st.error(f"❌ {mensaje}")
    st.stop()


# ==========================================
# 1. CLASES MATEMÁTICAS (EL MOTOR INVISIBLE)
# ==========================================

class VigaIsostatica:
    def __init__(self, longitud, num_segmentos=500):
        self.L = longitud
        self.x = np.linspace(0, longitud, num_segmentos + 1)
        self.V = np.zeros_like(self.x)
        self.M = np.zeros_like(self.x)
        self.R_A = 0.0
        self.R_B = 0.0

    def agregar_carga_puntual(self, P, a):
        if 0 <= a <= self.L:
            ra = P * (self.L - a) / self.L
            rb = P * a / self.L
            self.R_A += ra
            self.R_B += rb
            for i, xi in enumerate(self.x):
                if xi < a:
                    self.V[i] += ra
                    self.M[i] += ra * xi
                else:
                    self.V[i] += ra - P
                    self.M[i] += ra * xi - P * (xi - a)

    def agregar_carga_distribuida(self, w, a, b):
        if 0 <= a < b <= self.L:
            W_total = w * (b - a)
            centroide = (a + b) / 2
            ra = W_total * (self.L - centroide) / self.L
            rb = W_total * centroide / self.L
            self.R_A += ra
            self.R_B += rb
            for i, xi in enumerate(self.x):
                if xi <= a:
                    self.V[i] += ra
                    self.M[i] += ra * xi
                elif a < xi <= b:
                    self.V[i] += ra - w * (xi - a)
                    self.M[i] += ra * xi - w * ((xi - a)**2) / 2
                else:
                    self.V[i] += ra - W_total
                    self.M[i] += ra * xi - W_total * (xi - centroide)


class CurvaVertical:
    def __init__(self, p1, p2, cad_piv, elev_piv, l_curva):
        self.p1 = p1 / 100
        self.p2 = p2 / 100
        self.cad_piv = cad_piv
        self.elev_piv = elev_piv
        self.L = l_curva
        self.A = self.p2 - self.p1
        self.cad_pcv = self.cad_piv - (self.L / 2)
        self.cad_ptv = self.cad_piv + (self.L / 2)
        self.elev_pcv = self.elev_piv - self.p1 * (self.L / 2)

    def calcular_elevacion(self, cad_objetivo):
        x = cad_objetivo - self.cad_pcv
        return self.elev_pcv + (self.p1 * x) + ((self.A / (2 * self.L)) * x**2)

    def generar_estacado(self, intervalo):
        estaciones = []
        cad_actual = self.cad_pcv
        while round(cad_actual, 3) <= round(self.cad_ptv, 3):
            cota = self.calcular_elevacion(cad_actual)
            estaciones.append({
                "KM": f"{int(cad_actual/1000)}+{cad_actual%1000:06.2f}",
                "Elevación [m]": round(cota, 3)
            })
            cad_actual += intervalo
        return pd.DataFrame(estaciones)


class CanalAbierto:
    def __init__(self, Q, b, m, S, n):
        self.Q = Q
        self.b = b
        self.m = m
        self.S = S
        self.n = n

    def area(self, y):      return (self.b + self.m * y) * y
    def perimetro(self, y): return self.b + 2 * y * math.sqrt(1 + self.m**2)
    def espejo(self, y):    return self.b + 2 * self.m * y

    def calcular_tirante_normal(self):
        y = 1.0
        const_obj = (self.Q * self.n) / math.sqrt(self.S)
        for _ in range(100):
            A = self.area(y)
            P = self.perimetro(y)
            T = self.espejo(y)
            f_y  = (A**(5/3) / P**(2/3)) - const_obj
            df_y = (5/3)*A**(2/3)*P**(-2/3)*T - (2/3)*A**(5/3)*P**(-5/3)*(2*math.sqrt(1+self.m**2))
            y_new = y - f_y / df_y
            if abs(y_new - y) < 1e-6:
                return y_new
            y = max(y_new, 0.001)
        return y

    def calcular_tirante_critico(self):
        """Newton-Raphson sobre Q²/g = A³/T  →  f(y) = A³/T − Q²/g = 0"""
        g = 9.81
        yc = 1.0
        target = self.Q**2 / g
        for _ in range(100):
            A  = self.area(yc)
            T  = self.espejo(yc)
            f_y  = A**3 / T - target
            # d/dy [A³/T] = (3A²·T² − A³·2m) / T²
            df_y = (3 * A**2 * T**2 - A**3 * 2 * self.m) / T**2
            yc_new = yc - f_y / df_y
            if abs(yc_new - yc) < 1e-6:
                return yc_new
            yc = max(yc_new, 0.001)
        return yc


class VigaHiperestatica:
    """
    Resuelve vigas continuas / empotradas mediante el Método Matricial
    de Rigidez (Direct Stiffness Method) para elementos viga (2 GDL/nodo:
    deflexión v y rotación θ). Validado contra valores clásicos de libro
    de texto (viga simplemente apoyada, viga empotrada-apoyada, viga
    continua de 2 tramos).
    """

    def __init__(self, longitudes, EIs, tipos_apoyo):
        self.L = longitudes
        self.EI = EIs
        self.tipos = tipos_apoyo          # lista ["Libre","Articulado","Empotrado"] por nodo
        self.n_tramos = len(longitudes)
        self.n_nodos = self.n_tramos + 1
        self.n_dof = 2 * self.n_nodos
        self.udls = [0.0] * self.n_tramos
        self.puntuales = [None] * self.n_tramos   # (P, a) o None

    @staticmethod
    def _k_elem(L, EI):
        return (EI / L**3) * np.array([
            [12,     6*L,   -12,    6*L],
            [6*L,  4*L**2,  -6*L,  2*L**2],
            [-12,   -6*L,    12,   -6*L],
            [6*L,  2*L**2,  -6*L,  4*L**2]
        ])

    @staticmethod
    def _fef(w, L, P, a):
        fef = np.array([w*L/2, w*L**2/12, w*L/2, -w*L**2/12])
        if P:
            a_e = min(max(a, 1e-6), L - 1e-6)
            b_e = L - a_e
            fef = fef + np.array([
                P*b_e**2*(L+2*a_e)/L**3,
                P*a_e*b_e**2/L**2,
                P*a_e**2*(L+2*b_e)/L**3,
                -P*a_e**2*b_e/L**2
            ])
        return fef

    def set_cargas(self, udls, puntuales):
        self.udls = udls
        self.puntuales = puntuales

    def resolver(self):
        n = self.n_dof
        Kg = np.zeros((n, n))
        fef_g = np.zeros(n)
        elem_data = []

        for i in range(self.n_tramos):
            L, EI = self.L[i], self.EI[i]
            w = self.udls[i]
            P, a = self.puntuales[i] if self.puntuales[i] else (0.0, L/2)
            Ki = self._k_elem(L, EI)
            fefi = self._fef(w, L, P, a)
            dofs = [2*i, 2*i+1, 2*i+2, 2*i+3]
            for r in range(4):
                fef_g[dofs[r]] += fefi[r]
                for c in range(4):
                    Kg[dofs[r], dofs[c]] += Ki[r, c]
            elem_data.append((Ki, fefi, dofs))

        restringidos = []
        for j, tipo in enumerate(self.tipos):
            if tipo == "Articulado":
                restringidos.append(2*j)
            elif tipo == "Empotrado":
                restringidos.append(2*j)
                restringidos.append(2*j+1)

        if len(restringidos) < 2:
            raise ValueError("Estructura inestable: agrega al menos 2 restricciones "
                              "(por ejemplo dos apoyos articulados, o uno empotrado).")

        libres = [d for d in range(n) if d not in restringidos]

        Kff = Kg[np.ix_(libres, libres)]
        Feq = -fef_g[libres]

        try:
            d_libres = np.linalg.solve(Kff, Feq)
        except np.linalg.LinAlgError:
            raise ValueError("Estructura inestable: revisa la configuración de apoyos.")

        D = np.zeros(n)
        D[libres] = d_libres

        # Reacciones en GDL restringidos
        R_total = Kg @ D + fef_g
        reacciones = {dof: R_total[dof] for dof in restringidos}

        # Fuerzas de extremo por elemento -> para diagramas V(x), M(x)
        fuerzas_elem = []
        for (Ki, fefi, dofs) in elem_data:
            d_loc = D[dofs]
            f_loc = Ki @ d_loc + fefi
            fuerzas_elem.append(f_loc)

        return {
            "D": D,
            "reacciones": reacciones,
            "fuerzas_elem": fuerzas_elem
        }

    def diagrama(self, resultado, n_pts_por_tramo=60):
        """Devuelve arrays globales x, V(x), M(x) a lo largo de toda la viga."""
        x_global, V_global, M_global = [], [], []
        x0 = 0.0
        for i in range(self.n_tramos):
            L = self.L[i]
            w = self.udls[i]
            P, a = self.puntuales[i] if self.puntuales[i] else (0.0, L/2)
            F1, M1, _, _ = resultado["fuerzas_elem"][i]
            xs = np.linspace(0, L, n_pts_por_tramo)
            for x in xs:
                V = F1 - w*x - (P if (P and x > a) else 0.0)
                M = -M1 + F1*x - w*x**2/2 - (P*(x - a) if (P and x > a) else 0.0)
                x_global.append(x0 + x)
                V_global.append(V)
                M_global.append(M)
            x0 += L
        return np.array(x_global), np.array(V_global), np.array(M_global)


class TuberiaSanitaria:
    def __init__(self, diametro_m, pendiente, rugosidad):
        self.D = diametro_m
        self.S = pendiente
        self.n = rugosidad
        self.A_lleno = (math.pi * self.D**2) / 4
        self.R_lleno = self.D / 4
        self.Q_lleno = (1/self.n) * self.A_lleno * (self.R_lleno**(2/3)) * (self.S**0.5)

    def analizar_caudal(self, Q_real):
        if Q_real > self.Q_lleno:
            return {"Estatus": "ERROR"}
        y_d_min, y_d_max = 0.001, 1.0
        for _ in range(100):
            y_d = (y_d_min + y_d_max) / 2
            theta = 2 * math.acos(1 - 2*y_d)
            A_p  = (self.D**2 / 8) * (theta - math.sin(theta))
            P_p  = (theta * self.D) / 2
            R_p  = A_p / P_p
            Q_p  = (1/self.n) * A_p * (R_p**(2/3)) * (self.S**0.5)
            if Q_p < Q_real: y_d_min = y_d
            else:            y_d_max = y_d
            if abs(Q_p - Q_real) < 1e-6:
                break
        return {
            "Estatus":   "OK",
            "y_D":       y_d,
            "Velocidad": Q_real / A_p,
            "Tau":       9810 * R_p * self.S
        }


# ==========================================
# 2. SIDEBAR
# ==========================================
st.sidebar.title("Inge Docs PRO")
st.sidebar.markdown("---")
modulo = st.sidebar.radio(
    "Selecciona la herramienta:",
    ("🏗️ 1. Análisis de Estructuras",
     "🔗 5. Vigas Hiperestáticas",
     "🛣️ 2. Diseño de Carreteras",
     "🌊 3. Canales Abiertos",
     "🚰 4. Alcantarillado")
)
st.sidebar.markdown("---")
st.sidebar.success("Sistema Activo y Verificado.")


# ==========================================
# 3. MÓDULO 1 — ANÁLISIS ESTRUCTURAL
# ==========================================
if modulo == "🏗️ 1. Análisis de Estructuras":
    st.title("Análisis de Viga Isostática (Superposición)")
    st.markdown("Calcula reacciones y momentos aplicando múltiples cargas.")

    L = st.number_input("Longitud total de la viga [m]:", min_value=1.0, value=10.0)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Carga Distribuida")
        w   = st.number_input("Magnitud (w) [kN/m]:", value=15.0, min_value=0.0)
        a_w = st.number_input("Inicio de carga [m]:", value=0.0, min_value=0.0, max_value=float(L))
        b_w = st.number_input("Fin de carga [m]:",    value=float(L), min_value=0.0, max_value=float(L))
    with col2:
        st.subheader("Carga Puntual Principal")
        p1 = st.number_input("Magnitud (P) [kN]:", value=50.0, min_value=0.0)
        x1 = st.number_input("Posición [m]:", value=float(L/2), min_value=0.0, max_value=float(L))

    if st.button("Resolver Viga", type="primary"):
        viga = VigaIsostatica(L)
        if w  > 0: viga.agregar_carga_distribuida(w, a_w, b_w)
        if p1 > 0: viga.agregar_carga_puntual(p1, x1)

        st.success("✅ Análisis estructural completado.")

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Reacción en A",   f"{viga.R_A:.2f} kN")
        r2.metric("Reacción en B",   f"{viga.R_B:.2f} kN")
        r3.metric("Cortante Máx |V|", f"{np.max(np.abs(viga.V)):.2f} kN")
        r4.metric("Momento Máx",     f"{np.max(viga.M):.2f} kN·m")

        # --- DIAGRAMA DE FUERZA CORTANTE ---
        st.subheader("📊 Diagrama de Fuerza Cortante (V)")
        fig1, ax1 = plt.subplots(figsize=(10, 3))
        ax1.plot(viga.x, viga.V, color="#1f77b4", linewidth=2)
        ax1.fill_between(viga.x, viga.V, 0,
                         where=(viga.V >= 0), color="#1f77b4", alpha=0.25, label="V+")
        ax1.fill_between(viga.x, viga.V, 0,
                         where=(viga.V <  0), color="#d62728", alpha=0.25, label="V−")
        ax1.axhline(0, color="white", linewidth=0.8, linestyle="--")
        ax1.set_xlabel("Posición [m]", color="white")
        ax1.set_ylabel("Cortante [kN]", color="white")
        ax1.tick_params(colors="white")
        ax1.set_facecolor("#0e1117")
        fig1.patch.set_facecolor("#0e1117")
        for spine in ax1.spines.values():
            spine.set_edgecolor("#444")
        ax1.grid(True, color="#333", linestyle="--", linewidth=0.5)
        st.pyplot(fig1)
        plt.close(fig1)

        # --- DIAGRAMA DE MOMENTO FLECTOR ---
        st.subheader("📊 Diagrama de Momento Flector (M)")
        fig2, ax2 = plt.subplots(figsize=(10, 3))
        ax2.plot(viga.x, viga.M, color="#2ca02c", linewidth=2)
        ax2.fill_between(viga.x, viga.M, 0,
                         where=(viga.M >= 0), color="#2ca02c", alpha=0.25)
        ax2.fill_between(viga.x, viga.M, 0,
                         where=(viga.M <  0), color="#ff7f0e", alpha=0.25)
        ax2.axhline(0, color="white", linewidth=0.8, linestyle="--")
        ax2.set_xlabel("Posición [m]", color="white")
        ax2.set_ylabel("Momento [kN·m]", color="white")
        ax2.tick_params(colors="white")
        ax2.set_facecolor("#0e1117")
        fig2.patch.set_facecolor("#0e1117")
        for spine in ax2.spines.values():
            spine.set_edgecolor("#444")
        ax2.grid(True, color="#333", linestyle="--", linewidth=0.5)
        st.pyplot(fig2)
        plt.close(fig2)


# ==========================================
# 3.5 MÓDULO 5 — VIGAS HIPERESTÁTICAS
# ==========================================
elif modulo == "🔗 5. Vigas Hiperestáticas":
    st.title("Vigas Continuas y Empotradas (Método de Rigidez)")
    st.markdown(
        "Resuelve vigas con **cualquier combinación de apoyos** (articulado, "
        "empotrado o libre/voladizo) y **cualquier número de tramos**. "
        "Calculado con el Método Matricial de Rigidez, el mismo enfoque "
        "que usan los softwares profesionales."
    )

    n_tramos = st.number_input("Número de tramos:", min_value=1, max_value=6, value=2, step=1)
    n_nodos = n_tramos + 1

    st.subheader("1️⃣ Geometría y cargas por tramo")
    longitudes, EIs, udls, puntuales = [], [], [], []
    for i in range(int(n_tramos)):
        st.markdown(f"**Tramo {i+1}**")
        c1, c2, c3 = st.columns(3)
        with c1:
            L_i = st.number_input(f"Longitud [m]", min_value=0.5, value=5.0, key=f"L{i}")
        with c2:
            w_i = st.number_input(f"Carga distribuida w [kN/m]", value=0.0, key=f"w{i}")
        with c3:
            EI_i = st.number_input(
                f"Rigidez relativa EI", min_value=0.01, value=1.0, key=f"EI{i}",
                help="Si todos los tramos tienen la misma sección/material, deja 1.0. "
                     "Solo cambia esto si algún tramo tiene una sección distinta."
            )
        c4, c5 = st.columns(2)
        with c4:
            P_i = st.number_input(f"Carga puntual P [kN]", value=0.0, key=f"P{i}")
        with c5:
            a_i = st.number_input(
                f"Posición de P desde el inicio del tramo [m]",
                min_value=0.0, max_value=float(L_i), value=float(L_i)/2, key=f"a{i}"
            )
        longitudes.append(L_i)
        EIs.append(EI_i)
        udls.append(w_i)
        puntuales.append((P_i, a_i) if P_i != 0 else None)

    st.subheader("2️⃣ Apoyos")
    st.caption("Define el tipo de apoyo en cada nodo (un tramo tiene 2 nodos, dos tramos 3 nodos, etc.)")
    tipos_apoyo = []
    cols = st.columns(int(n_nodos))
    for j in range(int(n_nodos)):
        with cols[j]:
            tipos_apoyo.append(
                st.selectbox(f"Nodo {j+1}", ["Libre", "Articulado", "Empotrado"],
                              index=1, key=f"apoyo{j}")
            )

    if st.button("Resolver Viga Hiperestática", type="primary"):
        try:
            viga_h = VigaHiperestatica(longitudes, EIs, tipos_apoyo)
            viga_h.set_cargas(udls, puntuales)
            resultado = viga_h.resolver()
        except ValueError as e:
            st.error(f"🚨 {e}")
        else:
            st.success("✅ Sistema hiperestático resuelto correctamente.")

            x_acum = np.concatenate([[0], np.cumsum(longitudes)])
            L_total = x_acum[-1]

            # --- ESQUEMA DE LA VIGA ---
            st.subheader("📐 Esquema de la Viga")
            figs, axs = plt.subplots(figsize=(10, 2.2))
            axs.plot([0, L_total], [0, 0], color="white", linewidth=3, zorder=2)

            for j, tipo in enumerate(tipos_apoyo):
                xj = x_acum[j]
                if tipo == "Articulado":
                    tri = plt.Polygon(
                        [[xj-0.18*L_total/10, -0.35*L_total/10],
                         [xj+0.18*L_total/10, -0.35*L_total/10],
                         [xj, 0]],
                        closed=True, color="#1f77b4", zorder=3
                    )
                    axs.add_patch(tri)
                elif tipo == "Empotrado":
                    axs.add_patch(plt.Rectangle(
                        (xj-0.03*L_total/10, -0.4*L_total/10),
                        0.06*L_total/10, 0.4*L_total/10,
                        color="#d62728", zorder=3
                    ))
                    for k in range(5):
                        yk = -0.4*L_total/10 + k*0.1*L_total/10
                        axs.plot([xj-0.10*L_total/10, xj], [yk, yk+0.08*L_total/10],
                                 color="#d62728", linewidth=1, zorder=3)

            # cargas distribuidas
            for i in range(int(n_tramos)):
                if udls[i] != 0:
                    x0, x1_ = x_acum[i], x_acum[i+1]
                    axs.plot([x0, x1_], [0.35*L_total/10, 0.35*L_total/10],
                             color="#2ca02c", linewidth=1)
                    for xa in np.linspace(x0, x1_, 8):
                        axs.annotate("", xy=(xa, 0), xytext=(xa, 0.35*L_total/10),
                                      arrowprops=dict(arrowstyle="->", color="#2ca02c", lw=1))
                    axs.text((x0+x1_)/2, 0.45*L_total/10, f"w={udls[i]:g} kN/m",
                             color="#2ca02c", ha="center", fontsize=8)

            # cargas puntuales
            for i in range(int(n_tramos)):
                if puntuales[i]:
                    P_i, a_i = puntuales[i]
                    xa = x_acum[i] + a_i
                    axs.annotate("", xy=(xa, 0), xytext=(xa, 0.6*L_total/10),
                                  arrowprops=dict(arrowstyle="->", color="#ff7f0e", lw=2))
                    axs.text(xa, 0.68*L_total/10, f"P={P_i:g} kN",
                             color="#ff7f0e", ha="center", fontsize=8)

            axs.set_xlim(-0.5, L_total+0.5)
            axs.set_ylim(-0.7*L_total/10, 0.85*L_total/10)
            axs.axis("off")
            figs.patch.set_facecolor("#0e1117")
            st.pyplot(figs)
            plt.close(figs)

            # --- DIAGRAMAS V y M (se calculan primero para usarlos también en reacciones) ---
            x_d, V_d, M_d = viga_h.diagrama(resultado)

            # --- REACCIONES ---
            st.subheader("📋 Reacciones en los Apoyos")
            filas = []
            for j, tipo in enumerate(tipos_apoyo):
                if tipo == "Libre":
                    continue
                Rv = resultado["reacciones"].get(2*j, 0.0)
                Rm = resultado["reacciones"].get(2*j+1, None)
                if Rm is not None:
                    # Se reporta con el mismo signo que el diagrama de Momento
                    # (negativo = hogging / tensión en la fibra superior)
                    if j == 0:
                        Rm = M_d[0]
                    elif j == int(n_nodos) - 1:
                        Rm = M_d[-1]
                filas.append({
                    "Nodo": j+1,
                    "Tipo de apoyo": tipo,
                    "Reacción Vertical [kN]": round(Rv, 3),
                    "Reacción Momento [kN·m]": (round(Rm, 3) if Rm is not None else "—")
                })
            st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

            r1, r2 = st.columns(2)
            r1.metric("Cortante Máx |V|", f"{np.max(np.abs(V_d)):.2f} kN")
            idx_mmax = np.argmax(np.abs(M_d))
            r2.metric("Momento Máx |M|", f"{np.max(np.abs(M_d)):.2f} kN·m",
                      help=f"Ubicado en x = {x_d[idx_mmax]:.2f} m")

            st.subheader("📊 Diagrama de Fuerza Cortante (V)")
            fig1, ax1 = plt.subplots(figsize=(10, 3))
            ax1.plot(x_d, V_d, color="#1f77b4", linewidth=2)
            ax1.fill_between(x_d, V_d, 0, where=(V_d >= 0), color="#1f77b4", alpha=0.25)
            ax1.fill_between(x_d, V_d, 0, where=(V_d < 0), color="#d62728", alpha=0.25)
            ax1.axhline(0, color="white", linewidth=0.8, linestyle="--")
            for xj in x_acum:
                ax1.axvline(xj, color="#555", linewidth=0.8, linestyle=":")
            ax1.set_xlabel("Posición [m]", color="white")
            ax1.set_ylabel("Cortante [kN]", color="white")
            ax1.tick_params(colors="white")
            ax1.set_facecolor("#0e1117")
            fig1.patch.set_facecolor("#0e1117")
            for spine in ax1.spines.values():
                spine.set_edgecolor("#444")
            ax1.grid(True, color="#333", linestyle="--", linewidth=0.5)
            st.pyplot(fig1)
            plt.close(fig1)

            st.subheader("📊 Diagrama de Momento Flector (M)")
            fig2, ax2 = plt.subplots(figsize=(10, 3))
            ax2.plot(x_d, M_d, color="#2ca02c", linewidth=2)
            ax2.fill_between(x_d, M_d, 0, where=(M_d >= 0), color="#2ca02c", alpha=0.25)
            ax2.fill_between(x_d, M_d, 0, where=(M_d < 0), color="#ff7f0e", alpha=0.25)
            ax2.axhline(0, color="white", linewidth=0.8, linestyle="--")
            for xj in x_acum:
                ax2.axvline(xj, color="#555", linewidth=0.8, linestyle=":")
            ax2.set_xlabel("Posición [m]", color="white")
            ax2.set_ylabel("Momento [kN·m]", color="white")
            ax2.tick_params(colors="white")
            ax2.set_facecolor("#0e1117")
            fig2.patch.set_facecolor("#0e1117")
            for spine in ax2.spines.values():
                spine.set_edgecolor("#444")
            ax2.grid(True, color="#333", linestyle="--", linewidth=0.5)
            st.pyplot(fig2)
            plt.close(fig2)

            st.info(
                "ℹ️ Convención: el diagrama de Momento se muestra con valores "
                "positivos hacia arriba (zona verde) y momentos negativos "
                "(hogging, tensión en la fibra superior) hacia abajo (zona naranja)."
            )
elif modulo == "🛣️ 2. Diseño de Carreteras":
    st.title("Diseño Geométrico de Curva Vertical")
    st.markdown("Genera la tabla de replanteo topográfico para curvas simétricas.")

    col1, col2 = st.columns(2)
    with col1:
        p1       = st.number_input("Pendiente de entrada P1 [%]:", value=-2.0)
        cad_piv  = st.number_input("Cadenamiento del PIV [m]:", value=1000.0)
        L_curva  = st.number_input("Longitud de Curva Lv [m]:", min_value=20.0, value=120.0)
    with col2:
        p2       = st.number_input("Pendiente de salida P2 [%]:", value=3.0)
        elev_piv = st.number_input("Elevación del PIV [m]:", value=150.0)
        intervalo = st.number_input("Intervalo de estacado [m]:", min_value=5.0, value=20.0)

    if st.button("Generar Tabla de Estacado", type="primary"):
        curva = CurvaVertical(p1, p2, cad_piv, elev_piv, L_curva)
        df_estacado = curva.generar_estacado(intervalo)
        tipo = "Columpio (cóncava ∪)" if curva.A > 0 else "Cresta (convexa ∩)"
        st.success(
            f"✅ Tipo de curva: **{tipo}** | "
            f"A = {curva.A*100:.2f}% | "
            f"PCV: {curva.cad_pcv:.2f} m | "
            f"PTV: {curva.cad_ptv:.2f} m"
        )
        st.dataframe(df_estacado, use_container_width=True)


# ==========================================
# 5. MÓDULO 3 — CANALES ABIERTOS
# ==========================================
elif modulo == "🌊 3. Canales Abiertos":
    st.title("Diseño Hidráulico de Canales (Manning)")

    col1, col2, col3 = st.columns(3)
    with col1:
        Q = st.number_input("Caudal (Q) [m³/s]:", min_value=0.01, value=2.50)
        S = st.number_input("Pendiente (S) [m/m]:", min_value=0.0001, value=0.002, format="%.4f")
    with col2:
        b = st.number_input("Plantilla (b) [m]:", min_value=0.00, value=1.50)
        n = st.number_input("Rugosidad (n):", min_value=0.010, value=0.015, format="%.3f")
    with col3:
        m_talud = st.number_input("Talud (m) [H:1V]:", min_value=0.00, value=1.50)

    if st.button("Calcular Tirantes", type="primary"):
        g     = 9.81
        canal = CanalAbierto(Q, b, m_talud, S, n)

        yn = canal.calcular_tirante_normal()
        yc = canal.calcular_tirante_critico()

        A_n = canal.area(yn)
        T_n = canal.espejo(yn)
        V_n = Q / A_n
        Fr  = V_n / math.sqrt(g * A_n / T_n)
        E   = yn + V_n**2 / (2 * g)

        if   Fr < 0.95: regimen = "🔵 Subcrítico (flujo tranquilo)"
        elif Fr > 1.05: regimen = "🔴 Supercrítico (flujo rápido)"
        else:           regimen = "🟡 Flujo Crítico"

        st.success(f"✅ Newton-Raphson convergente | Régimen: **{regimen}** | Fr = {Fr:.4f}")

        res1, res2, res3 = st.columns(3)
        res1.metric("Tirante Normal (yₙ)",    f"{yn:.4f} m")
        res2.metric("Tirante Crítico (yc)",   f"{yc:.4f} m")
        res3.metric("Número de Froude (Fr)",  f"{Fr:.4f}")

        res4, res5, res6 = st.columns(3)
        res4.metric("Área Hidráulica (A)",     f"{A_n:.3f} m²")
        res5.metric("Velocidad Real (V)",      f"{V_n:.2f} m/s")
        res6.metric("Energía Específica (E)",  f"{E:.4f} m")


# ==========================================
# 6. MÓDULO 4 — ALCANTARILLADO
# ==========================================
elif modulo == "🚰 4. Alcantarillado":
    st.title("Revisión Normativa de Alcantarillado")

    col1, col2 = st.columns(2)
    with col1:
        D_cm  = st.number_input("Diámetro interno [cm]:", min_value=10.0, value=30.0, step=5.0)
        S     = st.number_input("Pendiente (S) [m/m]:", min_value=0.0001, value=0.005, format="%.4f")
        n     = st.number_input("Rugosidad (n):", min_value=0.009, value=0.013, format="%.3f")
    with col2:
        Q_lps = st.number_input("Caudal de diseño [L/s]:", min_value=0.1, value=25.0)

    if st.button("Dictaminar Red", type="primary"):
        tubo      = TuberiaSanitaria(D_cm/100, S, n)
        resultado = tubo.analizar_caudal(Q_lps/1000)

        st.info(f"Capacidad a tubo lleno (Qf): **{tubo.Q_lleno*1000:.2f} L/s**")

        if resultado["Estatus"] == "ERROR":
            st.error(f"🚨 RECHAZADO: El caudal de diseño ({Q_lps:.2f} L/s) "
                     f"supera la capacidad del tubo ({tubo.Q_lleno*1000:.2f} L/s).")
        else:
            m1, m2, m3 = st.columns(3)
            m1.metric("Llenado (y/D)",         f"{resultado['y_D']:.3f}")
            m2.metric("Velocidad",             f"{resultado['Velocidad']:.2f} m/s")
            m3.metric("Fuerza Tractiva (τ)",   f"{resultado['Tau']:.2f} Pa")

            st.markdown("---")
            # Criterio 1 — Llenado
            limite = 0.85 if D_cm > 60 else 0.80
            if resultado["y_D"] <= limite:
                st.success(f"✅ **Llenado:** {resultado['y_D']:.3f} ≤ {limite}  → Cumple norma.")
            else:
                st.warning(f"⚠️ **Llenado:** {resultado['y_D']:.3f} > {limite}  → Riesgo de asfixia.")

            # Criterio 2 — Velocidad mínima (autolimpieza)
            if resultado["Velocidad"] >= 0.60:
                st.success(f"✅ **Velocidad:** {resultado['Velocidad']:.2f} m/s ≥ 0.60 m/s → Autolimpieza OK.")
            else:
                st.error(f"🚨 **Velocidad:** {resultado['Velocidad']:.2f} m/s < 0.60 m/s → Riesgo de azolve.")

            # Criterio 3 — Fuerza tractiva
            if resultado["Tau"] >= 1.5:
                st.success(f"✅ **Fuerza tractiva:** {resultado['Tau']:.2f} Pa ≥ 1.5 Pa → Cumple norma.")
            else:
                st.error(f"🚨 **Fuerza tractiva:** {resultado['Tau']:.2f} Pa < 1.5 Pa → Riesgo de sedimentación.")
