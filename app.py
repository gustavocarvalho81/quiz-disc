from flask import Flask, render_template, request, jsonify
from sheets_manager import GoogleSheetsManager 
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
import os

app = Flask(__name__)
sheets_manager = GoogleSheetsManager()

load_dotenv()

QUIZ_CONTEXT = """
Você é um chatbot especializado em aplicar o assesment sobre DISC, para medir o nível cognitivo de conhecimento dos participantes de um workshop. Siga rigorosamente estas instruções:

ESTRUTURA DA CONVERSA:

1. BOAS-VINDAS (Sempre comece com):
Olá! 👋 Olá, a partir de agora, você responderá a algumas questões para analisar o ponto de partida da sua evolução sobre o tema Autoconhecimento.

2. EXPLICAÇÃO DO ASSESSMENT:
O tempo médio de resposta deste teste é de 4 minutos.

Lembre-se: você não precisa se preocupar ao responder essas questões, afinal, você não tem qualquer obrigação de conhecer este assunto.

Suas respostas nos ajudará a construir um material de apoio mais alinhado às necessidades do grupo e te mostrará, ao final do programa, o quanto você aprendeu sobre esse tema.

3. INSTRUÇÕES DE RESPOSTA:
Antes de começarmos, algumas instruções importantes:

- Você encontrará questões de múltipla escolha e escolha única
- Para responder, use as letras correspondentes às opções
- Em questões de múltipla escolha, separe suas respostas com vírgula (exemplo: a,b,c)
- Em questões de escolha única, use apenas uma letra (exemplo: a)

4. CONFIRMAÇÃO PARA INÍCIO:
Está pronto para começar? 😊

[Esperar resposta do usuário]

5. FORMATO DAS QUESTÕES:
[MÚLTIPLA ESCOLHA ✨] ou [ESCOLHA ÚNICA ⭐]

[Contextualização da pergunta]

a) Primeira opção
b) Segunda opção
[...]

QUESTIONÁRIO:

1. [MÚLTIPLA ESCOLHA ✨] 
Os profissionais que mais crescem profissionalmente, são aqueles que conhecem suas características individuais e tomam decisões pautadas em suas regras internas. Atualmente, é considerado um teste relevante para o autoconhecimento:

a) DISC (1.25 pontos)
b) BigFive (1.25 pontos)
c) MBTI (1.25 pontos)
d) Valores Motivacionais (1.25 pontos)
e) Nenhuma das anteriores (0 pontos)

2. [MÚLTIPLA ESCOLHA ✨]
Ao dominar a metodologia DISC, o profissional é capaz de se destacar em:

a) Comunicação e Gestão de Conflitos (1 ponto)
b) Inteligência Emocional (1 ponto)
c) Liderança e trabalho em equipe (1 ponto)
d) Produtividade e autoconfiança (1 ponto)
e) Vendas e Atendimento ao Cliente (1 ponto)

3. [MÚLTIPLA ESCOLHA ✨]
O DISC é uma metodologia que ajuda o profissional a identificar:

a) Seus pontos fortes e áreas de melhoria comportamentais (2 pontos)
b) O estilo de comunicação e tomada de decisão dos outros (2 pontos)
c) A melhor forma de delegar tarefas dentro da equipe (1 ponto)
d) O nível de motivação das outras pessoas na realização de atividades do dia a dia (-2 pontos)
e) O nível de motivação pessoal para diferentes tipos de atividades (-2 pontos)

4. [ESCOLHA ÚNICA ⭐]
Sobre liderança: dominar o DISC pode fazer com que o líder diminua em até 80% os conflitos internos com seus liderados, uma vez que a metodologia permite que o líder adapte seu estilo conforme as necessidades dos membros da equipe.

a) Verdadeiro (5 pontos)
b) Falso (0 pontos)

5. [MÚLTIPLA ESCOLHA ✨]
Sobre o padrão de perfil comportamental, quando uma pessoa passa muito tempo desempenhando atividades incoerentes ao perfil dela:

a) Se a adaptação do perfil for inconsciente, ele poderá apresentar queda de performance (0 pontos)
b) Se a adaptação do perfil for consciente e pontual, a performance do profissional não será prejudicada (1 ponto)
c) O profissional nunca demonstrará excepcionalidade no desempenho dessas atividades (1 ponto)
d) O profissional demorará muito mais tempo para realizar as atividades de maneira eficaz e terá um desgaste físico e mental muito maior (3 pontos)
e) Após três anos, ele assumirá um novo perfil comportamental natural (0 pontos)

Ao final do teste, você deve apenas enviar uma mensagem de agradecimento para o usuário.
"""

def get_gpt_response(prompt, conversation_history):
   try:
       messages = [
           {"role": "system", "content": QUIZ_CONTEXT},
           *conversation_history,
           {"role": "user", "content": prompt}
       ]
       
       client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
       response = client.chat.completions.create(
           model="gpt-3.5-turbo-instruct",
           messages=messages,
           temperature=0.7,
           max_tokens=500
       )
       
       return response.choices[0].message.content
   except Exception as e:
       return f"Erro ao processar resposta: {str(e)}"

def calculate_scores(responses):
   print("\nCalculando pontuações para as respostas:", responses)
   
   scores = {}
   
   question_scores = {
       '1': {'a': 1.25, 'b': 1.25, 'c': 1.25, 'd': 1.25, 'e': 0},
       '2': {'a': 1.0, 'b': 1.0, 'c': 1.0, 'd': 1.0, 'e': 1.0},
       '3': {'a': 2.0, 'b': 2.0, 'c': 1.0, 'd': -2.0, 'e': -2.0},
       '4': {'a': 5.0, 'b': 0},
       '5': {'a': 0, 'b': 1.0, 'c': 1.0, 'd': 3.0, 'e': 0}
   }
   
   for question_id, answers in responses.items():
       print(f"\nProcessando questão {question_id}")
       print(f"Respostas para esta questão: {answers}")
       
       scores[question_id] = 0
       for answer in answers:
           answer = answer.lower().strip()
           if answer in question_scores.get(str(question_id), {}):
               score = question_scores[str(question_id)][answer]
               scores[question_id] += score
               print(f"Resposta '{answer}' vale {score} pontos")
           else:
               print(f"Resposta '{answer}' não encontrada na tabela de pontuação")
   
   print("\nPontuações finais:", scores)
   return scores

@app.route('/')
def welcome():
   return render_template('welcome.html')

@app.route('/quiz')
def quiz():
   return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
   try:
       data = request.json
       user_message = data.get('message', '')
       session = data.get('session', {})
       user_data = data.get('user_data', {})
       
       print("\nMensagem recebida:", user_message)
       print("Sessão atual:", session)
       
       conversation_history = session.get('conversation_history', [])
       conversation_history.append({"role": "user", "content": user_message})
       
       if "começar o teste" in user_message.lower() or "sim" in user_message.lower():
           session = {
               'current_question': 0,
               'responses': {},
               'scores': {},
               'conversation_history': conversation_history
           }
       elif any(letter in user_message.lower() for letter in ['a', 'b', 'c', 'd', 'e']):
           if session.get('current_question', 0) == 0:
               session['current_question'] = 1
           
           current_question = str(session.get('current_question', 1))
           answers = [ans.strip().lower() for ans in user_message.split(',')]
           responses = session.get('responses', {})
           responses[current_question] = answers
           session['responses'] = responses
           
           print(f"Questão {current_question} - Respostas:", answers)
           
           scores = calculate_scores(responses)
           session['scores'] = scores
           print("Pontuações atualizadas:", scores)
           
           if session.get('current_question') == 5:
               print("\nTeste finalizado!")
               print("Respostas finais:", responses)
               print("Pontuações finais:", scores)
               try:
                   sheets_manager.save_response(user_data, responses, scores)
                   print("Dados salvos com sucesso na planilha!")
               except Exception as e:
                   print(f"Erro ao salvar na planilha: {str(e)}")
           else:
               session['current_question'] = session.get('current_question', 1) + 1
       
       bot_response = get_gpt_response(user_message, conversation_history)
       conversation_history.append({"role": "assistant", "content": bot_response})
       session['conversation_history'] = conversation_history
       
       return jsonify({
           'response': bot_response,
           'session': session
       })
       
   except Exception as e:
       print(f"Erro na rota chat: {str(e)}")
       return jsonify({
           'error': str(e),
           'message': 'Ocorreu um erro no processamento'
       }), 500

if __name__ == '__main__':
   app.run(host='0.0.0.0', port=10000)