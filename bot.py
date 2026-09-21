import telebot
import requests
import numpy as np
from datetime import datetime
import pytz

# --- CREDENCIALES ---
TOKEN_TELEGRAM = "8550036762:AAFGcOuR_NH57X6SZ0FSOlDq7tsXL7N1ZZo"
API_KEY_ODDS = "7959b532e8902fda20a1e347d79f8627"
BANKROLL_TOTAL = 1000.0  
FRACCION_KELLY = 0.25  

bot = telebot.TeleBot(TOKEN_TELEGRAM)

def simular_y_calcular(linea_casa, cuota_over, cuota_under):
    media_estimada = linea_casa + 0.8 
    sims = np.random.poisson(lam=media_estimada, size=10000)
    
    p_over = float(np.sum(sims > linea_casa) / 10000)
    p_under = 1.0 - p_over
    
    lado = "OVER" if p_over > p_under else "UNDER"
    prob = p_over if lado == "OVER" else p_under
    cuota = cuota_over if lado == "OVER" else cuota_under
    
    ev = (prob * cuota) - 1.0
    b = cuota - 1.0
    q = 1.0 - prob
    f_star = ((b * prob) - q) / b
    monto = round(BANKROLL_TOTAL * (f_star * FRACCION_KELLY), 2) if (f_star > 0 and ev >= 0.04) else 0.0
    
    return lado, prob, round(ev, 4), monto

@bot.message_handler(commands=['start'])
def enviar_bienvenida(mensaje):
    texto = (
        "🤖 Screener Cuantitativo Activo\n\n"
        "Comandos disponibles (Solo Partidos de Hoy):\n"
        "🏈 /analisis_nfl - Escanea picks de NFL\n"
        "⚾ /analisis_mlb - Escanea picks de MLB\n"
        "⚽ /analisis_ligamx - Escanea picks de Liga MX"
    )
    bot.reply_to(mensaje, texto)

def procesar_apuestas_bot(deporte_id, deporte_nombre):
    url = f"https://api.the-odds-api.com/v4/sports/{deporte_id}/odds/"
    parametros = {
        "apiKey": API_KEY_ODDS,
        "regions": "us",
        "markets": "totals",
        "oddsFormat": "decimal"
    }
    
    respuesta = requests.get(url, params=parametros)
    if respuesta.status_code != 200:
        return "❌ Error conectando con el radar de cuotas."
    
    datos = respuesta.json()
    zona_mx = pytz.timezone("America/Mexico_City")
    hoy = datetime.now(zona_mx).date() # Sacamos la fecha exacta de hoy
    
    mensaje = f"🚨 <b>BOLETA DE HOY: {deporte_nombre}</b> 🚨\n\n"
    
    encontrados = 0
    for juego in datos:
        # --- CANDADO DE FECHA ---
        fecha_utc = datetime.strptime(juego['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
        fecha_local_dt = fecha_utc.astimezone(zona_mx)
        
        # Si la fecha del partido no es igual a la fecha de hoy, saltamos al siguiente
        if fecha_local_dt.date() != hoy:
            continue
            
        if len(juego['bookmakers']) > 0:
            mercado = juego['bookmakers'][0]['markets'][0]
            if mercado['key'] == 'totals':
                over = next((o for o in mercado['outcomes'] if o['name'] == 'Over'), None)
                under = next((o for o in mercado['outcomes'] if o['name'] == 'Under'), None)
                
                if over and under:
                    lado, prob, ev, monto = simular_y_calcular(over['point'], over['price'], under['price'])
                    
                    if ev >= 0.04:
                        fecha_local = fecha_local_dt.strftime("%H:%M") # Solo mostramos la hora, ya sabemos que es hoy
                        
                        cuota_elegida = over['price'] if lado == "OVER" else under['price']
                        
                        mensaje += f"⏱ {fecha_local} hrs\n"
                        mensaje += f"⚔️ {juego['away_team']} vs {juego['home_team']}\n"
                        mensaje += f"🎯 Selección: <b>{lado} {over['point']}</b> (Cuota: {cuota_elegida})\n"
                        mensaje += f"📈 EV+: <b>+{ev*100:.1f}%</b> | 💰 Apuesta: <b>${monto} MXN</b>\n"
                        mensaje += "〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️\n"
                        encontrados += 1
                        
        if encontrados >= 5:
            break
            
    if encontrados == 0:
        return "❌ Ningún partido de HOY superó el filtro matemático."
        
    return mensaje

@bot.message_handler(commands=['analisis_nfl'])
def cmd_nfl(mensaje):
    bot.reply_to(mensaje, "⏳ Filtrando cartelera de HOY y corriendo simulaciones...")
    res = procesar_apuestas_bot("americanfootball_nfl", "NFL")
    bot.reply_to(mensaje, res, parse_mode="HTML")

@bot.message_handler(commands=['analisis_mlb'])
def cmd_mlb(mensaje):
    bot.reply_to(mensaje, "⏳ Filtrando cartelera de HOY y corriendo simulaciones...")
    res = procesar_apuestas_bot("baseball_mlb", "MLB")
    bot.reply_to(mensaje, res, parse_mode="HTML")

@bot.message_handler(commands=['analisis_ligamx'])
def cmd_ligamx(mensaje):
    bot.reply_to(mensaje, "⏳ Filtrando cartelera de HOY y corriendo simulaciones...")
    res = procesar_apuestas_bot("soccer_mexico_ligamx", "Liga MX")
    bot.reply_to(mensaje, res, parse_mode="HTML")

print("🟢 Bot inteligente encendido. Ve a Telegram y usa /start")
bot.infinity_polling()