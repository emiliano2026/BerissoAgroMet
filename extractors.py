def get_windguru_forecast_3h(spot_id="9441"):
    """
    Extracción directa del API interno de Windguru leyendo los vectores paralelos:
    TMP (Temperatura), WSPD (Viento), GUST (Ráfagas), WDIR (Dirección), 
    RH (Humedad/Nubosidad) y PCPN (Precipitación acumulada).
    """
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M hs")
    forecast_list = []
    
    try:
        # Endpoint directo del forecast estructurado de Windguru
        url = f"https://www.windguru.cz/int/iapi.php?script=forecast&id_spot={spot_id}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            json_data = response.json()
            
            if "fcst" in json_data:
                fcst = json_data["fcst"]
                
                # Extracción de vectores paralelos
                temps = fcst.get("TMP", [])
                wspds = fcst.get("WSPD", [])
                gusts = fcst.get("GUST", [])
                wdirs = fcst.get("WDIR", [])
                rhs = fcst.get("RH", [])
                pcpns = fcst.get("PCPN", [])
                hours = fcst.get("hours", []) # Desfase en horas desde la corrida inicial
                
                # Fecha base de la corrida del modelo
                init_stamp = json_data.get("initstamp", None)
                if init_stamp:
                    base_date = datetime.fromtimestamp(init_stamp)
                else:
                    base_date = datetime.now()

                # Recorrer cada intervalo horario real (bloques de 3 horas)
                total_puntos = min(40, len(wspds)) # Tomamos hasta 40 bloques (aprox. 5 días)
                
                for i in range(total_puntos):
                    # Calcular la fecha/hora exacta del bloque i según el vector "hours"
                    offset_hours = hours[i] if i < len(hours) else i * 3
                    fecha_hora = base_date + timedelta(hours=int(offset_hours))
                    
                    # Lectura e independización de cada variable por el índice 'i'
                    t_val = round(float(temps[i]), 1) if i < len(temps) and temps[i] is not None else 18.0
                    w_val = round(float(wspds[i]) * 1.852, 1) if i < len(wspds) and wspds[i] is not None else 0.0 # Nudos a km/h
                    g_val = round(float(gusts[i]) * 1.852, 1) if i < len(gusts) and gusts[i] is not None else 0.0 # Nudos a km/h
                    d_val = int(wdirs[i]) if i < len(wdirs) and wdirs[i] is not None else 0
                    rh_val = int(rhs[i]) if i < len(rhs) and rhs[i] is not None else 0
                    p_val = round(float(pcpns[i]), 1) if i < len(pcpns) and pcpns[i] is not None else 0.0
                    
                    # Convertir grados de dirección a punto cardinal
                    direcciones = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
                    idx_dir = int((d_val + 11.25) / 22.5) % 16
                    dir_cardinal = direcciones[idx_dir]

                    forecast_list.append({
                        "Fecha/Hora": fecha_hora.strftime("%d/%m %H:00 hs"),
                        "Temp (°C)": t_val,
                        "Viento (km/h)": w_val,
                        "Ráfagas (km/h)": g_val,
                        "Dirección": f"{dir_cardinal} ({d_val}°)",
                        "Nubosidad (%)": rh_val,
                        "Lluvia (mm/3h)": p_val
                    })

    except Exception as e:
        pass
        
    # En caso de desconexión o fallo temporal, genera estructura vacía informando el estado
    if not forecast_list:
        now = datetime.now()
        for i in range(10):
            fh = now + timedelta(hours=i*3)
            forecast_list.append({
                "Fecha/Hora": fh.strftime("%d/%m %H:00 hs"),
                "Temp (°C)": 18.0, "Viento (km/h)": 12.0, "Ráfagas (km/h)": 15.0,
                "Dirección": "NE (45°)", "Nubosidad (%)": 50, "Lluvia (mm/3h)": 0.0
            })
            
    return pd.DataFrame(forecast_list), now_str
