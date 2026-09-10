import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
# CONFIGURAÇÕES
# ==========================================

GRUPO = "Programação 2/26 B/Tarde"
CONTATO = "Lucas Rocha"

# ==========================================
# ABRIR WHATSAPP
# ==========================================

options = webdriver.ChromeOptions()
options.add_argument(r"--user-data-dir=C:\WhatsAppAutomacao")

driver = webdriver.Chrome(options=options)
driver.maximize_window()

driver.get("https://web.whatsapp.com/")

wait = WebDriverWait(driver, 180)

print("WhatsApp aberto.")

# ==========================================
# ESPERAR LOGIN
# ==========================================

print("Aguardando WhatsApp carregar...")

# Aguarda a interface principal
wait.until(
    EC.presence_of_element_located(
        (By.XPATH, '//div[@role="application"]')
    )
)

# Aguarda a barra de pesquisa
pesquisa = wait.until(
    EC.presence_of_element_located(
        (
            By.XPATH,
            '//div[@contenteditable="true"][@role="textbox"]'
        )
    )
)

print("WhatsApp pronto.")

time.sleep(3)

# ==========================================
# LOCALIZAR BARRA DE PESQUISA
# ==========================================

print("Procurando o grupo...")

caixas = driver.find_elements(
    By.XPATH,
    '//div[@contenteditable="true"][@role="textbox"]'
)

barra_pesquisa = None

for caixa in caixas:
    try:
        aria = caixa.get_attribute("aria-label")

        if aria and (
            "Pesquisar" in aria
            or "Search" in aria
        ):
            barra_pesquisa = caixa
            break

    except:
        pass

# Se não encontrou pelo aria-label,
# usa a primeira caixa visível da lateral
if barra_pesquisa is None:

    for caixa in caixas:

        try:
            if caixa.is_displayed():
                barra_pesquisa = caixa
                break
        except:
            pass

if barra_pesquisa is None:
    raise Exception("Barra de pesquisa não encontrada.")

# ==========================================
# PESQUISAR GRUPO
# ==========================================

barra_pesquisa.click()

# Limpa a pesquisa sem usar Enter
driver.execute_script(
    """
    arguments[0].focus();
    arguments[0].innerText = '';
    arguments[0].dispatchEvent(
        new InputEvent('input', {bubbles:true})
    );
    """,
    barra_pesquisa
)

barra_pesquisa.send_keys(GRUPO)

time.sleep(3)

# ==========================================
# CLICAR NO RESULTADO DO GRUPO
# ==========================================

print("Selecionando grupo...")

grupo = wait.until(
    EC.element_to_be_clickable(
        (
            By.XPATH,
            f'//*[normalize-space()="{GRUPO}"]'
        )
    )
)

driver.execute_script(
    "arguments[0].scrollIntoView({block:'center'});",
    grupo
)

time.sleep(1)

driver.execute_script(
    "arguments[0].click();",
    grupo
)

print("Grupo selecionado.")

# ==========================================
# ESPERAR CONVERSA ABRIR
# ==========================================

time.sleep(3)

print("Abrindo conversa...")

wait.until(
    EC.presence_of_element_located(
        (
            By.XPATH,
            '//footer//div[@contenteditable="true"]'
        )
    )
)

print("Conversa aberta.")

# ==========================================
# CAIXA DE MENSAGEM
# ==========================================

caixa_mensagem = wait.until(
    EC.element_to_be_clickable(
        (
            By.XPATH,
            '//footer//div[@contenteditable="true"][@role="textbox"]'
        )
    )
)

caixa_mensagem.click()

# ==========================================
# DIGITAR MENÇÃO
# ==========================================

print("Digitando @Lucas Rocha...")

caixa_mensagem.send_keys("@" + CONTATO)

time.sleep(3)

# ==========================================
# SELECIONAR LUCAS ROCHA
# ==========================================

print("Selecionando Lucas Rocha...")

mencao = None

seletores = [
    f'//*[@role="option"]//*[contains(text(),"{CONTATO}")]',
    f'//*[contains(@data-testid,"typeahead")]//*[contains(text(),"{CONTATO}")]',
    f'//span[contains(text(),"{CONTATO}")]'
]

for xpath in seletores:

    elementos = driver.find_elements(
        By.XPATH,
        xpath
    )

    for elemento in elementos:

        try:

            if elemento.is_displayed():

                mencao = elemento
                break

        except:
            pass

    if mencao:
        break

if mencao is None:
    raise Exception(
        "Lucas Rocha não apareceu na lista de menções."
    )

driver.execute_script(
    "arguments[0].click();",
    mencao
)

print("Lucas Rocha selecionado.")

time.sleep(2)

# ==========================================
# ENVIAR
# ==========================================

print("Procurando botão de enviar...")

botao_enviar = None

seletores_enviar = [
    '//button[@aria-label="Enviar"]',
    '//button[@aria-label="Send"]',
    '//button[@data-testid="compose-btn-send"]',
    '//*[@data-icon="send"]/ancestor::button[1]',
    '//*[@data-icon="send"]/ancestor::*[@role="button"][1]'
]

for xpath in seletores_enviar:

    elementos = driver.find_elements(
        By.XPATH,
        xpath
    )

    for elemento in elementos:

        try:

            if elemento.is_displayed() and elemento.is_enabled():

                botao_enviar = elemento
                break

        except:
            pass

    if botao_enviar:
        break

if botao_enviar is None:
    raise Exception(
        "Botão de enviar não encontrado."
    )

driver.execute_script(
    "arguments[0].click();",
    botao_enviar
)

print("===================================")
print("MENÇÃO ENVIADA COM SUCESSO!")
print("===================================")

# ==========================================
# FINAL
# ==========================================

time.sleep(5)
driver.quit()