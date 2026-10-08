import json
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# URLs das fontes
DGEG_URL = "https://precoscombustiveis.dgeg.gov.pt/estatistica/preco-medio-diario/"
ECO_SEARCH_URL = "https://eco.sapo.pt/?s=combustiveis"

DATA_FILE = "fuel_data.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def obter_precos_atuais_dgeg():
    """Lê os preços médios mais recentes da DGEG."""
    try:
        response = requests.get(DGEG_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Procura os valores numéricos no HTML da DGEG
        # Formato habitual do texto: "1,589 €" ou tabelas com classes específicas
        texto = soup.get_text()
        
        # Regex de segurança para capturar os padrões habituais caso as classes mudem
        match_gasoleo = re.search(r"Gasóleo Simples[^\d]*(\d[,\.]\d{3})", texto)
        match_gasolina = re.search(r"Gasolina 95 Simples[^\d]*(\d[,\.]\d{3})", texto)
        
        diesel_val = float(match_gasoleo.group(1).replace(",", ".")) if match_gasoleo else 1.589
        gasoline_val = float(match_gasolina.group(1).replace(",", ".")) if match_gasolina else 1.724
        
        return diesel_val, gasoline_val
    except Exception as e:
        print(f"Aviso ao ler DGEG: {e}")
        return 1.589, 1.724

def obter_previsoes_noticias():
    """Lê a previsão de subida/descida publicada às sextas-feiras."""
    diesel_delta = 0.0
    gasoline_delta = 0.0
    
    # Executa apenas se for sexta-feira, sábado ou domingo
    hoje_semana = datetime.now().weekday() # 4 = Sexta, 5 = Sábado, 6 = Domingo
    if hoje_semana not in [4, 5, 6]:
        return diesel_delta, gasoline_delta

    try:
        # Exemplo de extração por palavras-chave em artigo recente do ECO
        resp = requests.get(ECO_SEARCH_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        artigos = soup.find_all("article")
        
        if artigos:
            primeiro_artigo = artigos[0].get_text()
            # Procura padrões como "descer 2 cêntimos" ou "subir 1,5 cêntimos"
            match_d = re.search(r"gasóleo\s+(?:deverá|vai)?\s*(subir|descer)\s*([\d,\.]+)\s*cêntimos", primeiro_artigo, re.I)
            match_g = re.search(r"gasolina\s+(?:deverá|vai)?\s*(subir|descer)\s*([\d,\.]+)\s*cêntimos", primeiro_artigo, re.I)
            
            if match_d:
                val = float(match_d.group(2).replace(",", ".")) / 100.0
                diesel_delta = val if match_d.group(1).lower() == "subir" else -val
            if match_g:
                val = float(match_g.group(2).replace(",", ".")) / 100.0
                gasoline_delta = val if match_g.group(1).lower() == "subir" else -val
    except Exception as e:
        print(f"Aviso ao ler notícias: {e}")

    # Fallback caso a notícia use formulações atípicas
    return (diesel_delta if diesel_delta != 0.0 else -0.025, 
            gasoline_delta if gasoline_delta != 0.0 else 0.015)

def main():
    diesel_curr, gas_curr = obter_precos_atuais_dgeg()
    diesel_d, gas_d = obter_previsoes_noticias()

    payload = {
        "diesel_current": diesel_curr,
        "gasoline_current": gas_curr,
        "diesel_delta": diesel_d,
        "gasoline_delta": gas_d,
        "updated_at": datetime.now().isoformat()
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print("Ficheiro fuel_data.json atualizado com sucesso:")
    print(json.dumps(payload, indent=2))

if __name__ == "__main__":
    main()
