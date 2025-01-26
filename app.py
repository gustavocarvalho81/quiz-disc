from flask import Flask, render_template, request, jsonify
from sheets_manager import GoogleSheetsManager 
from dotenv import load_dotenv
from datetime import datetime
import os
import openai

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
Está pronto para começar? Responda "sim" ou "não".😊

[Esperar resposta do usuário]

5. FORMATO DAS QUESTÕES:
[MÚLTIPLA ESCOLHA ✨] ou [ESCOLHA ÚNICA ⭐]

[Contextualização da pergunta]

a) Primeira opção
b) Segunda opção
[...]

QUESTIONÁRIO:

1. Os profissionais que mais crescem profissionalmente são aqueles que conhecem suas características individuais e tomam decisões pautadas em suas regras internas. Atualmente, é/são considerado(s) teste(s) relevante(s) para o autoconhecimento:

a) DISC
b) BigFive
c) MBTI
d) Valores Motivacionais
e) Nenhuma das anteriores

Escolha quantas opções você julgar como correta. Ao responder, separe a(s) alternativa(s) por vírgula.

2. Ao dominar a metodologia DISC, o profissional é capaz de se destacar em:

a) Comunicação e Gestão de Conflitos 
b) Inteligência Emocional 
c) Liderança e trabalho em equipe 
d) Produtividade e autoconfiança 
e) Vendas e Atendimento ao Cliente

Escolha quantas opções você julgar como correta. Ao responder, separe a(s) alternativa(s) por vírgula.

3. O DISC é uma metodologia que ajuda o profissional a identificar:

a) Seus pontos fortes e pontos de fragilidade de comportamento 
b) Seu estilo de comunicação e o estilo de comunicação das outras pessoas
c) Ajuda o líder a escolher a melhor forma de delegar tarefas para os diferentes liderados da equipe 
d) O nível de motivação das outras pessoas na realização de atividades do dia a dia
e) O nível de motivação pessoal para diferentes tipos de atividades

Escolha quantas opções você julgar como correta. Ao responder, separe a(s) alternativa(s) por vírgula.

4. Sobre liderança: dominar o DISC pode fazer com que o líder diminua em até 80% os conflitos internos com seus liderados, uma vez que a metodologia permite que o líder adapte seu estilo conforme as necessidades dos membros da equipe.

a) Verdadeiro
b) Falso

5. Sobre o padrão de perfil comportamental, quando uma pessoa passa muito tempo desempenhando atividades incoerentes ao perfil dela:

a) Se a adaptação do perfil for inconsciente, ele poderá apresentar queda de performance
b) Se a adaptação do perfil for consciente e pontual, a performance do profissional não será prejudicada
c) O profissional nunca demonstrará excepcionalidade no desempenho dessas atividades
d) O profissional demorará muito mais tempo para realizar as atividades de maneira eficaz e terá um desgaste físico e mental muito maior
e) Após três anos, ele assumirá um novo perfil comportamental natural

Escolha quantas opções você julgar como correta. Ao responder, separe a(s) alternativa(s) por vírgula.

CONCLUSÃO:

Ao final do teste, você deve apenas enviar uma mensagem de agradecimento para o usuário.
"""
import openai
openai.api_key = os.getenv('OPENAI_API_KEY')

def get_gpt_response(prompt, conversation_history):
    try:                        
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",           
            messages=[
                {"role": "system", "content": QUIZ_CONTEXT},
                *conversation_history,
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message['content']
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