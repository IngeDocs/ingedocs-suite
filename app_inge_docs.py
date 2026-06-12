# -*- coding: utf-8 -*-
"""
Created on Thu Jun 11 17:43:41 2026

@author: victo
"""

"""
Plataforma Web Inge Docs - Suite de Ingeniería Civil PRO (COMPLETA)
Autor: Inge Docs
Descripción: Aplicación web interactiva con los 4 módulos profesionales.
"""

import streamlit as st
# --- SISTEMA DE DEFENSA INGE DOCS ---
st.title("🔒 Acceso Restringido - Inge Docs PRO")
clave = st.text_input("Ingresa la clave maestra que viene en tu manual PDF:", type="password")

if clave != "INGEDOCS-2026":
    st.warning("⚠️ Sistema bloqueado. Adquiere tu acceso oficial para utilizar las herramientas.")
    st.stop() # Este es el cadenero: detiene la lectura del código aquí mismo

st.success("✅ ¡Acceso Autorizado! Cargando módulos de ingeniería...")
st.divider()
# --- FIN DEL SISTEMA DE DEFENSA ---


import numpy as np
import pandas as pd
import math

# ==========================================
# 1. CLASES MATEMÁTICAS (EL MOTOR INVISIBLE)
# ==========================================

class VigaIsostatica:
    def __init__(self, longitud, num_segmentos=100):
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
            estaciones.append({"KM": f"{int(cad_actual/1000)}+{cad_actual%1000:06.2f}", 
                               "Elevación [m]": round(cota, 3)})
            cad_actual += intervalo
        return pd.DataFrame(estaciones)

class CanalAbierto:
    def __init__(self, Q, b, m, S, n):
        self.Q = Q
        self.b = b
        self.m = m
        self.S = S
        self.n = n

    def area(self, y): return (self.b + self.m * y) * y
    def perimetro(self, y): return self.b + 2 * y * math.sqrt(1 + self.m**2)
    def espejo(self, y): return self.b + 2 * self.m * y

    def calcular_tirante_normal(self):
        y = 1.0
        const_obj = (self.Q * self.n) / math.sqrt(self.S)
        for _ in range(100):
            A, P, T = self.area(y), self.perimetro(y), self.espejo(y)
            f_y = (A**(5/3) / P**(2/3)) - const_obj
            df_dy = (5/3)*A**(2/3)*P**(-2/3)*T - (2/3)*A**(5/3)*P**(-5/3)*(2*math.sqrt(1+self.m**2))
            y_new = y - f_y / df_dy
            if abs(y_new - y) < 1e-6: return y_new
            y = y_new
        return y

class TuberiaSanitaria:
    def __init__(self, diametro_m, pendiente, rugosidad):
        self.D = diametro_m
        self.S = pendiente
        self.n = rugosidad
        self.A_lleno = (math.pi * self.D**2) / 4
        self.R_lleno = self.D / 4
        self.Q_lleno = (1/self.n) * self.A_lleno * (self.R_lleno**(2/3)) * (self.S**0.5)

    def analizar_caudal(self, Q_real):
        if Q_real > self.Q_lleno: return {"Estatus": "ERROR"}
        y_d_min, y_d_max = 0.001, 1.0
        for _ in range(100):
            y_d = (y_d_min + y_d_max) / 2
            theta = 2 * math.acos(1 - 2*y_d)
            A_p = (self.D**2 / 8) * (theta - math.sin(theta))
            P_p = (theta * self.D) / 2
            R_p = A_p / P_p
            Q_p = (1/self.n) * A_p * (R_p**(2/3)) * (self.S**0.5)
            if Q_p < Q_real: y_d_min = y_d
            else: y_d_max = y_d
            if abs(Q_p - Q_real) < 1e-6: break
        return {"Estatus": "OK", "y_D": y_d, "Velocidad": Q_real / A_p, "Tau": 9810 * R_p * self.S}

# ==========================================
# 2. CONFIGURACIÓN DE LA PÁGINA WEB
# ==========================================
st.set_page_config(page_title="Suite Inge Docs", page_icon="🏗️", layout="wide")

st.sidebar.title("Inge Docs PRO")
st.sidebar.markdown("---")
modulo = st.sidebar.radio(
    "Selecciona la herramienta:",
    ("🏗️ 1. Análisis de Estructuras", 
     "🛣️ 2. Diseño de Carreteras", 
     "🌊 3. Canales Abiertos", 
     "🚰 4. Alcantarillado")
)
st.sidebar.markdown("---")
st.sidebar.success("Sistema Activo y Verificado.")

# ==========================================
# 3. INTERFAZ GRÁFICA (LOS 4 MÓDULOS)
# ==========================================

# --- MÓDULO 1: ESTRUCTURAS ---
if modulo == "🏗️ 1. Análisis de Estructuras":
    st.title("Análisis de Viga Isostática (Superposición)")
    st.markdown("Calcula reacciones y momentos aplicando múltiples cargas.")
    
    L = st.number_input("Longitud total de la viga [m]:", min_value=1.0, value=10.0)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Carga Distribuida")
        w = st.number_input("Magnitud (w) [kN/m]:", value=15.0)
        a_w = st.number_input("Inicio de carga [m]:", value=0.0, max_value=L)
        b_w = st.number_input("Fin de carga [m]:", value=L, max_value=L)
    
    with col2:
        st.subheader("Carga Puntual Principal")
        p1 = st.number_input("Magnitud (P) [kN]:", value=50.0)
        x1 = st.number_input("Posición [m]:", value=L/2, max_value=L)
        
    if st.button("Resolver Viga", type="primary"):
        viga = VigaIsostatica(L)
        if w > 0: viga.agregar_carga_distribuida(w, a_w, b_w)
        if p1 > 0: viga.agregar_carga_puntual(p1, x1)
        
        st.success("Análisis estructural completado.")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Reacción en A", f"{viga.R_A:.2f} kN")
        r2.metric("Reacción en B", f"{viga.R_B:.2f} kN")
        r3.metric("Cortante Máx", f"{np.max(np.abs(viga.V)):.2f} kN")
        r4.metric("Momento Máx", f"{np.max(viga.M):.2f} kN-m")
        
        st.subheader("Diagrama de Momento Flector")
        # Streamlit grafica automáticamente los arreglos de numpy
        df_momentos = pd.DataFrame({'Momento [kN-m]': viga.M}, index=viga.x)
        st.line_chart(df_momentos)

# --- MÓDULO 2: CARRETERAS ---
elif modulo == "🛣️ 2. Diseño de Carreteras":
    st.title("Diseño Geométrico de Curva Vertical")
    st.markdown("Genera la tabla de replanteo topográfico para curvas simétricas.")
    
    col1, col2 = st.columns(2)
    with col1:
        p1 = st.number_input("Pendiente de entrada P1 [%]:", value=-2.0)
        cad_piv = st.number_input("Cadenamiento del PIV [m]:", value=1000.0)
        L_curva = st.number_input("Longitud de Curva Lv [m]:", min_value=20.0, value=120.0)
    with col2:
        p2 = st.number_input("Pendiente de salida P2 [%]:", value=3.0)
        elev_piv = st.number_input("Elevación del PIV [m]:", value=150.0)
        intervalo = st.number_input("Intervalo de estacado [m]:", min_value=5.0, value=20.0)
        
    if st.button("Generar Tabla de Estacado", type="primary"):
        curva = CurvaVertical(p1, p2, cad_piv, elev_piv, L_curva)
        df_estacado = curva.generar_estacado(intervalo)
        
        st.success(f"Curva generada con éxito. Diferencia algebraica A = {curva.A*100:.2f}%")
        st.dataframe(df_estacado, use_container_width=True)

# --- MÓDULO 3: CANALES ---
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
        m = st.number_input("Talud (m) [H:1V]:", min_value=0.00, value=1.50)
        
    if st.button("Calcular Tirante Normal", type="primary"):
        canal = CanalAbierto(Q, b, m, S, n)
        yn = canal.calcular_tirante_normal()
        A_n = canal.area(yn)
        V_n = Q / A_n
        
        st.success("Iteración de Newton-Raphson convergente.")
        res1, res2, res3 = st.columns(3)
        res1.metric("Tirante Normal ($y_n$)", f"{yn:.4f} m")
        res2.metric("Área Hidráulica", f"{A_n:.3f} m²")
        res3.metric("Velocidad Real", f"{V_n:.2f} m/s")

# --- MÓDULO 4: ALCANTARILLADO ---
elif modulo == "🚰 4. Alcantarillado":
    st.title("Revisión Normativa de Alcantarillado")
    
    col1, col2 = st.columns(2)
    with col1:
        D_cm = st.number_input("Diámetro interno [cm]:", min_value=10.0, value=30.0, step=5.0)
        S = st.number_input("Pendiente (S) [m/m]:", min_value=0.0001, value=0.005, format="%.4f")
        n = st.number_input("Rugosidad (n):", min_value=0.009, value=0.013, format="%.3f")
    with col2:
        Q_lps = st.number_input("Caudal de diseño [L/s]:", min_value=0.1, value=25.0)
        
    if st.button("Dictaminar Red", type="primary"):
        tubo = TuberiaSanitaria(D_cm/100, S, n)
        resultados = tubo.analizar_caudal(Q_lps/1000)
        
        if resultados["Estatus"] == "ERROR":
            st.error(f"🚨 RECHAZADO: Caudal excede capacidad a tubo lleno ({tubo.Q_lleno*1000:.2f} L/s).")
        else:
            m1, m2, m3 = st.columns(3)
            m1.metric("Llenado (y/D)", f"{resultados['y_D']:.2f}")
            m2.metric("Velocidad", f"{resultados['Velocidad']:.2f} m/s")
            m3.metric("Tractiva (τ)", f"{resultados['Tau']:.2f} Pa")
            
            limite = 0.85 if D_cm > 60 else 0.80
            if resultados['y_D'] <= limite: st.success("✅ **Llenado:** Cumple norma.")
            else: st.warning("⚠️ **Llenado:** Riesgo de asfixia del tubo.")
            
            if resultados['Tau'] >= 1.5 or resultados['Velocidad'] >= 0.6: st.success("✅ **Limpieza:** Cumple norma.")
            else: st.error("🚨 **Limpieza:** Riesgo de azolve.")