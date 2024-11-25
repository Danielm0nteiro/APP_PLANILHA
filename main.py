from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import pandas as pd
import os
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Necessário para usar flash messages

UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Processar o arquivo enviado
        uploaded_file = request.files['file']
        if uploaded_file.filename != '':
            file_ext = os.path.splitext(uploaded_file.filename)[1].lower()
            if file_ext not in ['.xls', '.xlsx']:
                flash('Por favor, envie um arquivo Excel (.xls ou .xlsx).')
                return redirect(request.url)

            # Salvar o arquivo com um nome único
            unique_filename = str(uuid.uuid4()) + file_ext
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            uploaded_file.save(file_path)

            # Números para remover
            numeros_para_remover = request.form.get('numeros_remover').splitlines()
            numeros_para_remover = [num.strip() for num in numeros_para_remover if num.strip()]

            # Nome da coluna de contatos
            coluna_contato = request.form.get('coluna_contato').strip()

            # Número máximo de linhas por planilha
            try:
                max_linhas_por_planilha = int(request.form.get('max_linhas_por_planilha'))
                if max_linhas_por_planilha <= 0:
                    raise ValueError('O número máximo de linhas deve ser um valor positivo.')
            except ValueError:
                flash('O número máximo de linhas deve ser um valor válido.')
                return redirect(request.url)

            try:
                # Processar a planilha
                processar_planilha(file_path, numeros_para_remover, coluna_contato, max_linhas_por_planilha)
            except ValueError as e:
                flash(str(e))
                return redirect(request.url)

            return redirect(url_for('download'))

    return render_template('index.html')

@app.route('/download', methods=['GET'])
def download():
    files = os.listdir(PROCESSED_FOLDER)
    return render_template('download.html', files=files)

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(PROCESSED_FOLDER, filename)
    return send_file(file_path, as_attachment=True)

def gerar_variacoes(numero):
    """Gera variações de um número de telefone."""
    numero = numero.lstrip('55')
    ddd = numero[:2]
    restante = numero[2:]
    sem_9 = restante[1:] if restante.startswith('9') else restante

    variacoes = [
        f"55{ddd}{restante}",  # Com código do país
        f"{ddd}{restante}",   # Sem código do país
        f"{restante}",        # Sem DDD
        f"{sem_9}"           # Sem DDD e sem o dígito 9
    ]
    return variacoes

def processar_planilha(file_path, numeros_para_remover, coluna_contato, max_linhas_por_planilha):
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        raise ValueError('Erro ao ler o arquivo Excel: ' + str(e))

    if coluna_contato not in df.columns:
        raise ValueError(f'A coluna "{coluna_contato}" não foi encontrada na planilha.')

    # Converter todos os números para strings
    df[coluna_contato] = df[coluna_contato].astype(str)

    # Gerar variações para cada número a ser removido
    todas_variacoes = []
    for numero in numeros_para_remover:
        todas_variacoes.extend(gerar_variacoes(numero))

    # Remover duplicados e números indesejados
    df = df.drop_duplicates(subset=[coluna_contato])
    df = df[~df[coluna_contato].isin(todas_variacoes)]

    # Limpar arquivos antigos
    for file in os.listdir(PROCESSED_FOLDER):
        os.remove(os.path.join(PROCESSED_FOLDER, file))

    # Dividir em múltiplas planilhas
    for i in range(0, len(df), max_linhas_por_planilha):
        df_part = df.iloc[i:i + max_linhas_por_planilha]
        output_filename = f"PlanilhaUP_{i // max_linhas_por_planilha + 1}.xlsx"
        output_path = os.path.join(PROCESSED_FOLDER, output_filename)
        df_part.to_excel(output_path, index=False)

if __name__ == '__main__':
    app.run(debug=True)