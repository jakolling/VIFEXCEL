# WyScout-SkillCorner Merger App

## Description
App para mesclar dados do WyScout com métricas físicas do SkillCorner (Physical Output e Overcome Pressure), permitindo resolução manual de mismatches entre jogadores.

## Features
- Upload de arquivos Excel (WyScout e SkillCorner)
- Identificação automática de mismatches
- Interface para linkar manualmente jogadores não correspondentes
- Opção para excluir jogadores da base final
- Export para Excel do arquivo mesclado

## Setup
1. Clone o repositório
2. Instale as dependências:
```bash
pip install -r requirements.txt
```
3. Execute o app:
```bash
streamlit run app.py
```

## Uso
1. Faça upload dos 3 arquivos Excel:
   - Database WyScout
   - SkillCorner Physical Output
   - SkillCorner Overcome Pressure
2. Resolva os mismatches manualmente usando a interface
3. Baixe o arquivo Excel mesclado final

## Deploy
Para deploy no Streamlit Cloud:
1. Push para um repositório GitHub
2. Acesse streamlit.io/cloud
3. Conecte com seu GitHub
4. Selecione o repositório
5. Deploy