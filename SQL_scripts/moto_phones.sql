-- 1. Limpieza inicial
DROP TABLE IF EXISTS dispositivos_moviles;
DROP TABLE IF EXISTS especificaciones_producto;

-- 2. Creación de Tabla MOTOS con campos numéricos explícitos
CREATE TABLE especificaciones_producto (
    id SERIAL PRIMARY KEY,
    
    -- Información Básica (Texto)
    modelo_interno VARCHAR(50),
    nombre_comercial VARCHAR(100),
    cantidad_carga_40hq_texto VARCHAR(100),
    colores_disponibles VARCHAR(100),
    notas VARCHAR(255),
    
    -- Dimensiones (Texto)
    dimensiones_producto VARCHAR(100),
    
    -- Funciones (Texto)
    funciones_app TEXT,
    sistema_antirrobo TEXT,
    sistema_seguridad_ai TEXT,
    metodo_arranque VARCHAR(150),
    
    -- Rendimiento (Texto Original)
    autonomia_texto VARCHAR(150),
    velocidad_maxima_texto VARCHAR(100),
    carga_maxima_texto VARCHAR(100),
    torque_maximo_texto VARCHAR(100),
    potencia_pico_texto VARCHAR(100),
    capacidad_escalada_texto VARCHAR(50),
    distancia_al_suelo_texto VARCHAR(50),
    
    -- DATOS NUMÉRICOS PARA ANÁLISIS (NUEVO)
    autonomia_km_num INT,           -- Kilómetros
    velocidad_max_kmh INT,          -- Km/h
    carga_max_kg INT,               -- Kg
    torque_nm INT,                  -- N.m
    potencia_pico_w INT,            -- Watts
    potencia_nominal_w INT,         -- Watts
    grado_escalada_deg INT,         -- Grados (°)
    despeje_suelo_mm INT,           -- Milímetros
    tiempo_carga_horas DECIMAL(4,1),-- Horas
    peso_seco_kg DECIMAL(5,2),      -- Kg (sin batería)
    peso_total_kg DECIMAL(5,2),     -- Kg (con batería)
    bateria_voltaje_v INT,          -- Voltios
    bateria_amperaje_ah INT,        -- Amperios-hora
    cantidad_40hq_num INT,          -- Cantidad en contenedor
    
    -- Componentes (Texto)
    tiempo_carga_texto VARCHAR(50),
    suspension_delantera VARCHAR(100),
    suspension_trasera VARCHAR(100),
    tipo_asiento VARCHAR(100),
    impermeabilidad VARCHAR(50),
    puerto_usb VARCHAR(50),
    audio_bluetooth VARCHAR(50),
    modo_reparacion_un_clic TEXT,
    
    -- Motor y Transmisión
    tipo_motor VARCHAR(100),
    especificacion_iman VARCHAR(100),
    potencia_nominal_texto VARCHAR(50),
    tipo_transmision VARCHAR(50),
    
    -- Frenos y Ruedas
    tipo_frenos VARCHAR(100),
    modo_freno VARCHAR(50),
    tipo_llanta VARCHAR(100),
    especificacion_neumatico VARCHAR(50),
    
    -- Batería
    tipo_bateria VARCHAR(100),
    especificacion_bateria_texto VARCHAR(50),
    cargador VARCHAR(150),
    
    -- Peso y Empaque
    peso_seco_texto VARCHAR(50),
    peso_total_texto VARCHAR(50),
    tipo_empaque VARCHAR(50),
    dimensiones_empaque VARCHAR(100),
    
    imagen VARCHAR(255),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Creación de Tabla MOVILES con campos numéricos explícitos
CREATE TABLE dispositivos_moviles (
    id SERIAL PRIMARY KEY,
    
    -- Clasificación
    marca VARCHAR(50),
    categoria VARCHAR(50),
    modelo VARCHAR(100),
    
    -- Especificaciones (Texto Original)
    pantalla_texto TEXT,
    procesador VARCHAR(150),
    memoria_texto VARCHAR(150),
    bateria_texto VARCHAR(100),
    carga_texto VARCHAR(100),
    
    -- DATOS NUMÉRICOS PARA ANÁLISIS (NUEVO)
    pantalla_pulgadas DECIMAL(4,2), -- Pulgadas
    refresco_pantalla_hz INT,       -- Hz
    ram_gb INT,                     -- GB
    rom_gb INT,                     -- GB
    bateria_mah INT,                -- mAh
    carga_w INT,                    -- Watts
    camara_principal_mp INT,        -- Megapíxeles
    precio_num DECIMAL(10,2),       -- Precio numérico
    
    -- Multimedia
    camaras_texto TEXT,
    sistema_operativo VARCHAR(100),
    
    -- Otros
    extras TEXT,
    puntos_venta_clave TEXT,
    precio_promocion_texto VARCHAR(50),
    
    imagen VARCHAR(255), 
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Inserción de Datos MOTOS (Con valores numéricos extraídos)
INSERT INTO especificaciones_producto (
    -- Texto
    modelo_interno, nombre_comercial, cantidad_carga_40hq_texto, colores_disponibles, notas,
    dimensiones_producto, funciones_app, sistema_antirrobo, sistema_seguridad_ai, metodo_arranque,
    autonomia_texto, velocidad_maxima_texto, carga_maxima_texto, torque_maximo_texto, potencia_pico_texto,
    capacidad_escalada_texto, distancia_al_suelo_texto, tiempo_carga_texto,
    suspension_delantera, suspension_trasera, tipo_asiento, impermeabilidad, puerto_usb, audio_bluetooth, modo_reparacion_un_clic,
    tipo_motor, especificacion_iman, potencia_nominal_texto, tipo_transmision,
    tipo_frenos, modo_freno, tipo_llanta, especificacion_neumatico,
    tipo_bateria, especificacion_bateria_texto, cargador,
    peso_seco_texto, peso_total_texto, tipo_empaque, dimensiones_empaque, imagen,
    -- Numéricos
    autonomia_km_num, velocidad_max_kmh, carga_max_kg, torque_nm, potencia_pico_w, potencia_nominal_w,
    grado_escalada_deg, despeje_suelo_mm, tiempo_carga_horas, peso_seco_kg, peso_total_kg,
    bateria_voltaje_v, bateria_amperaje_ah, cantidad_40hq_num
) VALUES 
(
    'XMM', 'ATHENA', '249 unidades', 'Azul/Negro/Verde', NULL,
    'L1405*W650*H1000mm',
    'APP un toque, Timbre buscador, Gestión multi-vehículo, Tienda, Post-venta, Trayectoria, Login biométrico',
    'Bloqueo motor, Armado auto, Alarma rotación/vibración, GPS',
    'Predicción colisión AI', 'Llave física, BT, APP',
    '100±8Km (80kg); 62±8Km (125kg)', '42km/h', '125Kg (Segura)', '46N.m', '600W',
    '15°', '130mm', '6-8H',
    'Horquilla reforzada', 'Resorte completo', 'Asiento dividido', 'IP65', 'No', 'No', NULL,
    'Cubo imán permanente', '20H1.6T', '500W', 'Eje',
    'Tambor 110 (Del/Tras)', 'Freno mano', 'Hierro', '2.75-10 Vacío',
    'Plomo-ácido (Tianneng)', '60V20Ah', 'AC:100-264V 50/60HZ 3A',
    '35.5Kg', '66Kg', 'SKD', 'L1235*W310*H685mm', NULL,
    -- Numéricos extraídos
    100, 42, 125, 46, 600, 500, 15, 130, 8.0, 35.50, 66.00, 60, 20, 249
),
(
    'U2-Edición Rider', 'CORVUS D', '160 unidades', 'Verde/Rojo', 'Garantía batería 2 años',
    '1700*680*1010 mm',
    'APP un toque, Buscador, Gestión multi-vehículo, Tienda, Post-venta, Trayectoria, Apertura cajuela remota',
    'Bloqueo motor, Armado auto, Alarma rotación/vibración, GPS',
    'Predicción colisión AI', 'Llave física, BT, NFC, APP',
    '91±8Km (80kg); 60±8Km (125kg)', '63Km/h', '135Kg', '86N.m', '1200W',
    '20°', '120mm', '6-8H',
    'Hidráulica 27#', 'Hidráulica tubo 30', 'Una pieza', 'IP65', '5V/1A', 'Sí', 'Sí',
    'Cubo imán permanente', '30H1.8T', '1000W', 'Eje',
    'Disco 180 (Del/Tras)', 'Freno mano', 'Aluminio MT2.15-12', '3.00-10 Vacío',
    'Litio-Ferrofosfato', '60V20AH', '100-264V 50/60HZ 3A',
    '55.34kg', '65.5kg', 'SKD', 'L1480*W370*H760mm', NULL,
    -- Numéricos extraídos
    91, 63, 135, 86, 1200, 1000, 20, 120, 8.0, 55.34, 65.50, 60, 20, 160
),
(
    'U2-Usuario', 'CORVUS P+', '160 unidades', 'Amarillo/Verde/Blanco', 'Garantía batería 5 años',
    '1700*680*1010 mm',
    'APP un toque, Buscador, Gestión multi-vehículo, Tienda, Post-venta, Trayectoria, Login biométrico, Apertura cajuela',
    'Bloqueo motor, Armado auto, Alarma rotación/vibración, GPS',
    'Predicción colisión AI', 'Llave física, BT, NFC, APP',
    '130±8Km (80kg); 80±8Km (125kg) (Teórico)', '63Km/h', '135Kg', '86N.m', '1200W',
    '20°', '120mm', '6-8H',
    'Hidráulica 27#', 'Hidráulica tubo 30', 'Una pieza', 'IP65', '5V/1A', 'Sí', 'Sí',
    'Cubo imán permanente', '30H1.8T', '1000W', 'Eje',
    'Disco 180 (Del/Tras)', 'Freno mano', 'Aluminio MT2.15-12', '3.00-10 Vacío',
    'Litio-Ferrofosfato (New Energy)', '64V33AH', '100-264V 50/60HZ 4A',
    '55.34kg', 'TBD', 'SKD', 'L1480*W370*H760mm', NULL,
    -- Numéricos extraídos
    130, 63, 135, 86, 1200, 1000, 20, 120, 8.0, 55.34, NULL, 64, 33, 160
),
(
    'BJ1-3', 'ATHENA X2', '198 unidades', 'Rojo/Gris Nebula/Verde/Beige', 'Pedido mín 2 contenedores',
    '1850*605*1050mm',
    'APP un toque, Buscador, Gestión multi-vehículo, Tienda, Post-venta, Trayectoria, Login biométrico, Apertura cajuela',
    'Bloqueo motor, Armado auto, Alarma rotación/vibración, GPS',
    'Predicción colisión AI', 'Llave física, BT, NFC, APP',
    '90±8Km (80kg); 50±8Km (125kg)', '42Km/h', '135Kg', '66N.m', '700W',
    '15°', '120mm', '6-8H',
    'Hidráulica disco', 'Resorte completo', 'Una pieza', 'IP65', 'No', 'Sí', 'Sí',
    'Cubo imán permanente', '24H1.7T', '600W', 'Eje',
    'Del: Disco 180 / Tras: Tambor 110', 'Freno mano', 'Hierro', '2.75-10 Vacío',
    'Plomo-ácido (Tianneng)', '60V20Ah', 'AC:100-264V 50/60HZ 3A',
    '52Kg', '82.5KG', 'SKD', 'L1380*W330*H780mm', NULL,
    -- Numéricos extraídos
    90, 42, 135, 66, 700, 600, 15, 120, 8.0, 52.00, 82.50, 60, 20, 198
),
(
    'BQ1', 'URSA F', '140 unidades', 'Rosa/Gris/Blanco', '/',
    '1655*620*1090mm',
    'APP un toque, Buscador, Gestión multi-vehículo, Tienda, Post-venta, Trayectoria, Login biométrico',
    'Bloqueo motor, Armado auto, Alarma rotación/vibración, GPS',
    'Predicción colisión AI', 'Llave física, BT, NFC, APP',
    '100±8Km (80kg); 70±8Km (125kg)', '63Km/h', '135Kg', '86N.m', '1200W',
    '20°', '120mm', '6-8H',
    'Hidráulica 27#', 'Resorte hidráulico 24#', 'Una pieza', 'IP65', '5V/1A', 'Sí', 'Sí',
    'Cubo imán permanente', '30H1.8T', '1000W', 'Eje',
    'Del: Disco 180 / Tras: Tambor 110', 'Freno mano', 'Del: Aluminio / Tras: Hierro', '3.00-10 Vacío',
    'Plomo-ácido (Tianneng)', '72V20Ah', '100-264V 50/60HZ 3A',
    '49.5kg', '87kg', 'SKD', 'L1620*W430*H780mm', NULL,
    -- Numéricos extraídos
    100, 63, 135, 86, 1200, 1000, 20, 120, 8.0, 49.50, 87.00, 72, 20, 140
),
(
    'ZM', 'URSA F+', '230 unidades', 'Naranja/Azul/Rojo', '/',
    '1670*705*1045mm',
    'APP un toque, Buscador, Gestión multi-vehículo, Tienda, Post-venta, Trayectoria, Login biométrico, Apertura cajuela',
    'Bloqueo motor, Armado auto, Alarma rotación/vibración, GPS',
    'Predicción colisión AI', 'Llave física, BT, NFC, APP',
    '99±8Km (80kg); 72±8Km (125kg)', '63Km/h', '135Kg', '86N.m', '1200W',
    '20°', '120mm', '6-8H',
    'Hidráulica 27#', 'Resorte hidráulico 24#', 'Una pieza', 'IP65', '5V/1A', 'Sí', 'Sí',
    'Cubo imán permanente', '30H1.8T', '1000W', 'Eje',
    'Disco 180 (Del/Tras)', 'Freno mano', 'Del: Aluminio / Tras: Hierro', '3.00-10 Vacío',
    'Plomo-ácido (Tianneng)', '72V20Ah', '100-264V 50/60HZ 3A',
    '53kg', '90.5kg', 'SKD', 'L1460*W380*H815mm', NULL,
    -- Numéricos extraídos
    99, 63, 135, 86, 1200, 1000, 20, 120, 8.0, 53.00, 90.50, 72, 20, 230
),
(
    'T18S', 'CORVUS P', '100 unidades', 'Blanco Metal/Púrpura/Gris', '/',
    '1700*680*1100mm',
    'APP un toque, Buscador, Gestión multi-vehículo, Tienda, Post-venta, Trayectoria, Login biométrico, Apertura cajuela',
    'Bloqueo motor, Armado auto, Alarma rotación/vibración, GPS',
    'Predicción colisión AI', 'Llave física, BT, NFC, APP',
    '140±8Km (80kg); 93±8Km (125kg)', '64Km/h', '135Kg', '100N.M', '1800W',
    '20°', '130mm', '6-8H',
    'Hidráulica φ30', 'Hidráulica φ30', 'Una pieza', 'IP65', '5V/1A', 'Sí', 'Sí',
    'Motor de Cubo (Hub Motor)', '35H Gran Potencia', '1200W', 'Transmisión Motor Directa',
    'Disco/Disco', 'Freno mano', 'Hierro', '3.0-10 Vacío',
    'Plomo-ácido (Tianneng)', '72V32Ah', '100-264V 50/60HZ 4A',
    '65.88KG', '120KG', 'SKD', 'L1800*W510*H870mm', NULL,
    -- Numéricos extraídos
    140, 64, 135, 100, 1800, 1200, 20, 130, 8.0, 65.88, 120.00, 72, 32, 100
);

-- 5. Inserción de Datos MOVILES (Con valores numéricos extraídos)
INSERT INTO dispositivos_moviles (
    marca, categoria, modelo,
    pantalla_texto, procesador, memoria_texto, bateria_texto, carga_texto,
    camaras_texto, sistema_operativo, extras, puntos_venta_clave, precio_promocion_texto, imagen,
    -- Numéricos
    pantalla_pulgadas, refresco_pantalla_hz, ram_gb, rom_gb, bateria_mah, carga_w, camara_principal_mp, precio_num
) VALUES
('Redmi', 'Smartphone', 'Redmi 14C', 
 '6.88" HD+ LCD 120Hz (260ppi, 600nits), TÜV Rheinland', 'MediaTek Helio G81-Ultra (Octa-core 2.0GHz)', 
 '4GB + 4GB Virtual / 128GB (Exp. 1TB)', '5160 mAh', '18W (100% en 114 min)', 
 'Principal 50MP + QVGA, Frontal 13MP (f/2.0)', 'HyperOs / Android 14', 
 'Huella lateral, Jack 3.5mm, Volumen 150%', 'Pantalla inmersiva más grande del segmento (6.88")...', NULL, NULL,
 -- Numéricos
 6.88, 120, 4, 128, 5160, 18, 50, NULL),

('Redmi', 'Smartphone', 'REDMI A5', 
 '6.88" AdaptiveSync 120Hz LCD HD+, 450 nits, TÜV Rheinland', 'UNISOC T7250 Octa-core 1.8GHz', 
 '3GB / 64GB (Exp. 2TB)', '5200mAh', '15W', 
 'Trasera Dual 32MP (f/2.0) + QVGA, Frontal 8MP', 'Android 15', 
 'Desbloqueo facial/dactilar, Jack 3.5mm, Wet Touch', 'Pantalla Inmersiva 6.88". Cámara Dual 32MP con AI.', NULL, NULL,
 -- Numéricos
 6.88, 120, 3, 64, 5200, 15, 32, NULL),

('Redmi', 'Smartphone', 'Redmi 13 4G', 
 '6.79" FHD 90 Hz', 'Mediatek Helio G91 Ultra', 
 '6GB/8GB + 128GB/256GB', '5030 mAh', '33 W', 
 'Dual 108+2 MP, Frontal 13 MP', 'Android 14 / Hyper OS', 
 NULL, 'Dual Cámara de 108MP. Batería 5030 mAh, Carga 33W.', NULL, NULL,
 -- Numéricos
 6.79, 90, 6, 256, 5030, 33, 108, NULL),

('Redmi', 'Smartphone', 'Redmi Note 13 4G', 
 '6.67" FHD Amoled 120 Hz', 'Snapdragon 685', 
 '6GB/8GB + 128GB/256GB/512GB (Exp. 1 Tb)', '5000 mAh', '33 W', 
 'Triple 108+8+2 MP, Frontal 16 MP', 'Android 13', 
 NULL, 'Cámara 108MP. Memoria hasta 1TB. Pantalla Amoled 120Hz.', NULL, NULL,
 -- Numéricos
 6.67, 120, 6, 512, 5000, 33, 108, NULL),

('Redmi', 'Smartphone', 'Redmi Note 13 Pro (4G)', 
 '6.67" FHD Amoled 120 Hz, IP 54', 'MediaTek Helio G99-Ultra', 
 '8 GB + 256 GB', '5000 mAh', '67 W', 
 'Triple 200+8+2 MP, Frontal 16 MP', 'Android 13', 
 'IP 54', 'Cámara 200MP. Carga 67W. IP54.', NULL, NULL,
 -- Numéricos
 6.67, 120, 8, 256, 5000, 67, 200, NULL),

('Redmi', 'Smartphone', 'Redmi Note 13 Pro 5G', 
 '6.67" AMOLED 1.5K 120 Hz, IP 54', 'Snapdragon 7s Gen 2', 
 '8GB/12GB + 256GB/512GB', '5100 mAh', '67 W', 
 'Triple 200+8+2 MP OIS, Frontal 16 MP', 'Android 13', 
 'IP 54', 'Cámara 200MP OIS. Pantalla 1.5K AMOLED. Carga 67W.', NULL, NULL,
 -- Numéricos
 6.67, 120, 8, 512, 5100, 67, 200, NULL),

('Redmi', 'Smartphone', 'Redmi Note 13 Pro+ 5G', 
 '6.67" AMOLED 1.5K 120Hz, IP 54', 'Mediatek Dimensity 7200 Ultra', 
 '12 GB + 512 GB', '5000 mAh', '120W', 
 'Triple 200+8+2 MP OIS, Frontal 16 MP', 'Android 14', 
 'IP 54', 'Carga Rápida 120W. Cámara 200MP OIS.', NULL, NULL,
 -- Numéricos
 6.67, 120, 12, 512, 5000, 120, 200, NULL),

('Redmi', 'Smartphone', 'Redmi A3x', 
 'LCD HD+ 6.71" 90Hz', 'Unisoc T603 1.8GHz', 
 '4 + 128 GB', '5000mAh', '10W', 
 '8 MP + QVGA, Frontal 5 MP', 'Android 14', 
 NULL, 'Económico.', '$1,999', NULL,
 -- Numéricos
 6.71, 90, 4, 128, 5000, 10, 8, 1999.00),

('Redmi', 'Smartphone', 'Redmi 13C', 
 'LCD HD+ 6.74" 90Hz', 'MediaTek Helio G85', 
 '4 + 128 GB', '5000mAh', '18W', 
 '50 + 2 MP + QVGA, Frontal 8 MP', 'Android 13', 
 NULL, 'Calidad precio.', '$2,499', NULL,
 -- Numéricos
 6.74, 90, 4, 128, 5000, 18, 50, 2499.00),

('Redmi', 'Tablet', 'Redmi Pad SE', 
 'FHD 11" 90Hz', 'Snapdragon 680 4G', 
 '8 + 256 GB (Exp. 1 Tb)', '8000mAh', '10W', 
 'Trasera 8 MP, Frontal 5 MP', NULL, 
 '4 altavoces Dolby Atmos, Diseño Metal Unibody', 'Audio y Diseño Premium.', NULL, NULL,
 -- Numéricos
 11.00, 90, 8, 256, 8000, 10, 8, NULL),

('Redmi', 'Tablet', 'Redmi Pad Pro', 
 'LCD 2.5K 12.1" 120Hz', 'Snapdragon 7s Gen 2', 
 '8 + 256 GB', '10000mAh', '33W', 
 'Trasera 8 MP, Frontal 8 MP', 'Android 14', 
 NULL, 'Batería 10000mAh. Pantalla 2.5K 120Hz.', NULL, NULL,
 -- Numéricos
 12.10, 120, 8, 256, 10000, 33, 8, NULL),

('Xiaomi', 'Tablet', 'Xiaomi Pad 6', 
 'WQHD+ 2.8K 11" 144Hz', 'Snapdragon 870 5G', 
 '6 + 128 GB', '8840mAh', '33W', 
 'Trasera 13 MP, Frontal 8 MP', 'Android 13', 
 'IP54, 4 Speakers', 'Pantalla Ultra Fluida 144Hz. Procesador potente SD 870.', NULL, NULL,
 -- Numéricos
 11.00, 144, 6, 128, 8840, 33, 13, NULL),

('HONOR', 'Smartphone', 'HONOR X8c', 
 'AMOLED 6.7" FHD+ 120Hz (2800nits), SGS', 'Snapdragon 685', 
 '8GB + 512GB (16GB RAM Turbo)', '5000mAh', '35W SuperCharge', 
 '108MP OIS+EIS + 5MP Gran Angular, Frontal 50MP Flash', 'MagicOS 9.0 (Android 15)', 
 'IP64, Magic Capsule, Magic Portal', 'Primer Smartphone con Borrador IA...', NULL, NULL,
 -- Numéricos
 6.70, 120, 8, 512, 5000, 35, 108, NULL),

('HONOR', 'Smartphone', 'HONOR X7c', 
 'LCD 6.77" HD+ 120Hz, SGS 5 Estrellas', 'Snapdragon 685', 
 '8GB + 256GB (16GB RAM Turbo)', '5200mAh', '35W SuperCharge', 
 '108MP + 2MP Profundidad, Frontal 8MP', 'MagicOS 8.0 (Android 14)', 
 'IP64, Altavoces estéreo (300% vol)', 'Resistencia 360° certificada...', NULL, NULL,
 -- Numéricos
 6.77, 120, 8, 256, 5200, 35, 108, NULL),

('HONOR', 'Smartphone', 'HONOR X6b', 
 'LCD 6.56" HD+ 90Hz', 'MediaTek Helio G85', 
 '6GB+6GB (RAM Turbo) / 256GB (Exp. 1TB)', '5200mAh', '35W SuperCharge', 
 '50MP + 2MP Profundidad, Frontal 5MP', 'MagicOS 8.0', 
 'Magic Capsule', 'Batería duradera...', NULL, NULL,
 -- Numéricos
 6.56, 90, 6, 256, 5200, 35, 50, NULL),

('HONOR', 'Smartphone', 'HONOR Magic7 Lite', 
 'AMOLED 6.78" 1.5K 120Hz (4000 nits)', 'Snapdragon 6 Gen 1', 
 '8GB+8GB Turbo / 512GB', '6600mAh (Silicon-Carbon)', '66W SuperCharge', 
 '108MP (OIS) + 5MP, Frontal 16MP', 'MagicOS 8.0', 
 'IP65M, SGS 5 Estrellas', 'Súper Resistencia 3ra Gen...', NULL, NULL,
 -- Numéricos
 6.78, 120, 8, 512, 6600, 66, 108, NULL),

('HONOR', 'Smartphone', 'HONOR 200 Pro 5G', 
 'AMOLED 6.78" FHD+ 120Hz (4000 nits)', 'Snapdragon 8s Gen 3', 
 '12GB+12GB Turbo / 512GB', '5200mAh (Silicon-Carbon)', '100W SuperCharge (66W Inalámbrica)', 
 '50MP OIS + 50MP Tele (2.5x), Frontal 50MP 3D', 'MagicOS 8.0', 
 'IP65, Sonido estéreo, Magic Portal, Traducción', 'Cámara Profesional...', NULL, NULL,
 -- Numéricos
 6.78, 120, 12, 512, 5200, 100, 50, NULL),

('HONOR', 'Accesorio', 'HONOR CHOICE Portable Bluetooth Speaker', 
 NULL, NULL, 
 NULL, '1000 mAh (10 Horas)', NULL, 
 NULL, NULL, 
 'IP67, Bluetooth, Modo estéreo (dual pairing)', '10 Horas de música...', NULL, NULL,
 -- Numéricos
 NULL, NULL, NULL, NULL, 1000, NULL, NULL, NULL);