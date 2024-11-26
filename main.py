from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import pandas as pd
import os
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = ['.xls', '.xlsx', '.csv']

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        uploaded_file = request.files['file']
        if uploaded_file.filename != '':
            file_ext = os.path.splitext(uploaded_file.filename)[1].lower()
            if file_ext not in ALLOWED_EXTENSIONS:
                flash(f'Por favor, envie um arquivo nos formatos permitidos: {", ".join(ALLOWED_EXTENSIONS)}.')
                return redirect(request.url)

            unique_filename = str(uuid.uuid4()) + file_ext
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            uploaded_file.save(file_path)

            numeros_para_remover = request.form.get('numeros_remover').splitlines()
            numeros_para_remover = [num.strip() for num in numeros_para_remover if num.strip()]

            coluna_contato = request.form.get('coluna_contato').strip()

            try:
                max_linhas_por_planilha = int(request.form.get('max_linhas_por_planilha'))
                if max_linhas_por_planilha <= 0:
                    raise ValueError('O número máximo de linhas deve ser positivo.')
            except ValueError:
                flash('O número máximo de linhas deve ser válido.')
                return redirect(request.url)

            try:
                processar_planilha(file_path, numeros_para_remover, coluna_contato, max_linhas_por_planilha, file_ext)
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
    numero = numero.lstrip('55')
    ddd = numero[:2]
    restante = numero[2:]
    sem_9 = restante[1:] if restante.startswith('9') else restante

    variacoes = [
        f"55{ddd}{restante}",
        f"{ddd}{restante}",
        f"{restante}",
        f"{sem_9}"
    ]
    return variacoes

def processar_planilha(file_path, numeros_para_remover, coluna_contato, max_linhas_por_planilha, file_ext):
    try:
        if file_ext == '.csv':
            df = pd.read_csv(file_path)
        elif file_ext in ['.xls', '.xlsx']:
            df = pd.read_excel(file_path)
        else:
            raise ValueError('Formato de arquivo não suportado.')
    except Exception as e:
        raise ValueError('Erro ao ler o arquivo: ' + str(e))

    if coluna_contato not in df.columns:
        raise ValueError(f'A coluna "{coluna_contato}" não foi encontrada na planilha.')

    df[coluna_contato] = df[coluna_contato].astype(str)
    todas_variacoes = []
    for numero in numeros_para_remover:
        todas_variacoes.extend(gerar_variacoes(numero))

    df = df.drop_duplicates(subset=[coluna_contato])
    df = df[~df[coluna_contato].isin(todas_variacoes)]

    for file in os.listdir(PROCESSED_FOLDER):
        os.remove(os.path.join(PROCESSED_FOLDER, file))

    for i in range(0, len(df), max_linhas_por_planilha):
        df_part = df.iloc[i:i + max_linhas_por_planilha]
        output_filename = f"PlanilhaUP_{i // max_linhas_por_planilha + 1}{file_ext}"
        output_path = os.path.join(PROCESSED_FOLDER, output_filename)
        if file_ext == '.csv':
            df_part.to_csv(output_path, index=False)
        elif file_ext in ['.xls', '.xlsx']:
            df_part.to_excel(output_path, index=False)

if __name__ == '__main__':
    app.run(debug=True)
