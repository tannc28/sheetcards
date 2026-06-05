"""Default multilingual AI prompt templates (extracted from config_manager.py).

AI Help / Ask / Checker prompt dictionaries keyed by language code."""

AI_HELP_PROMPTS = {
    "en_us": """
        <command>
            I'm studying with flashcards and need help understanding this one better.
        </command>

        <card_content>
            {card_content}
        </card_content>

        <output_format>
            <h2>What is this card trying to teach me?</h2>
            <h2>What examples, contexts, and real situations does this information apply to?</h2>
            <h2>Why is this information important?</h2>
            <h2>How can I better remember this concept?</h2>
        </output_format>

        <output_details>
            Keep your explanation clear and concise.
            You must respond in American English.
            Never use markdown formatting or markdown bullets. 
            The response must always be formatted using HTML tags.
            Whenever convenient, use HTML lists (enumerated or bullet points) and bold text to make your response easier to read.
        </output_details>    
    """,
    "pt_br": """
        <command>
            Estou estudando com flashcards e preciso de ajuda para entender este cartão melhor.
        </command>

        <card_content>
            {card_content}
        </card_content>

        <output_format>
            <h2>O que este cartão está tentando me ensinar?</h2>
            <h2>Que exemplos, contextos e situações reais essa informação se aplica?</h2>
            <h2>Por que esta informação é importante?</h2>
            <h2>Como posso me lembrar melhor deste conceito?</h2>
        </output_format>

        <output_details>
            Mantenha sua explicação clara e concisa.
            Você deve responder em Português brasileiro.
            Nunca use formatação markdown ou marcadores markdown. 
            A resposta deve sempre ser formatada usando tags HTML.
            Sempre que conveniente, use listas HTML (numeradas ou com marcadores) e texto em negrito para facilitar a leitura da sua resposta.
        </output_details>
    """,
    "es_la": """
        <command>
            Estoy estudiando con tarjetas de memoria y necesito ayuda para entender esta tarjeta mejor.
        </command>

        <card_content>
            {card_content}
        </card_content>

        <output_format>
            <h2>¿Qué intenta enseñarme esta tarjeta?</h2>
            <h2>¿A qué ejemplos, contextos y situaciones reales se aplica esta información?</h2>
            <h2>¿Por qué es importante esta información?</h2>
            <h2>¿Cómo puedo recordar mejor este concepto?</h2>
        </output_format>

        <output_details>
            Mantén tu explicación clara y concisa.
            Usted debe responder en español latino.
            Nunca uses formato markdown ni viñetas markdown. 
            La respuesta debe estar siempre formateada usando etiquetas HTML.
            Siempre que sea conveniente, usa listas HTML (numeradas o con viñetas) y texto en negrita para facilitar la lectura de tu respuesta.
        </output_details>
    """,
}

# Default prompt template for AI Help (English)
DEFAULT_AI_HELP_PROMPT = AI_HELP_PROMPTS["en_us"]

# Default prompt templates for AI Ask (answering user questions)
AI_ASK_PROMPTS = {
    "en_us": """
        <command>
            I am studying with flashcards. Here is the card content for context:
        </command>

        <card_content>
            {card_content}
        </card_content>

        <question>
            {question}
        </question>

        <output_details>
            Keep your explanation clear and concise.
            You must respond in American English.
            Never use markdown formatting or markdown bullets. 
            The response must always be formatted using HTML tags.
            Whenever convenient, use HTML lists (enumerated or bullet points) and bold text to make your response easier to read.
        </output_details>  
    """,
    "pt_br": """
        <command>
            Estou estudando com flashcards. Aqui está o conteúdo do cartão para contexto:
        </command>

        <card_content>
            {card_content}
        </card_content>

        <question>
            {question}
        </question>

        <output_details>
            Mantenha sua explicação clara e concisa.
            Você deve responder em Português brasileiro.
            Nunca use formatação markdown ou marcadores markdown. 
            A resposta deve sempre ser formatada usando tags HTML.
            Sempre que conveniente, use listas HTML (numeradas ou com marcadores) e texto em negrito para facilitar a leitura da sua resposta.
        </output_details>
    """,
    "es_la": """
        <command>
            Estoy estudiando con tarjetas de memoria. Aquí está el contenido de la tarjeta como contexto:
        </command>

        <card_content>
            {card_content}
        </card_content>

        <question>
            {question}
        </question>

        <output_details>
            Mantén tu explicación clara y concisa.
            Usted debe responder en español latino.
            Nunca uses formato markdown ni viñetas markdown. 
            La respuesta debe estar siempre formateada usando etiquetas HTML.
            Siempre que sea conveniente, usa listas HTML (numeradas o con viñetas) y texto en negrita para facilitar la lectura de tu respuesta.
        </output_details>
    """,
}

# Default prompt templates for AI Checker (fact-checking and improvement)
AI_CHECKER_PROMPTS = {
    "en_us": """
        <command>
            I'm studying with flashcards and need help checking the quality of this one.
        </command>

        <card_content>
            {card_content}
        </card_content>

        <output_format>
            <h2>Is the information correct according to official/academic sources?</h2>
            <h2>Is the content coherent and logically well-structured?</h2>
            <h2>Is any part of the content outdated or no longer valid?</h2>
            <h2>Can the content be simplified or made clearer without losing meaning?</h2>
            <hr>
            <h2>Veredict</h2>
                ✅ Information is accurate and well-structured.
                ⚠️ Minor issues or room for improvement.
                ❌ Factual errors found that need correction.</h2>
            <hr>
            <h2>Suggest any improvements to make this card more effective for studying.</h2>
        </output_format>

        <output_details>
            Keep your explanation clear and concise.
            You must respond in American English.
            Never use markdown formatting or markdown bullets. 
            The response must always be formatted using HTML tags.
            Whenever convenient, use HTML lists (enumerated or bullet points) and bold text to make your response easier to read.
        </output_details>   
    """,
    "pt_br": """
        <command>
            Estou estudando com flashcards e preciso de ajuda para verificar a qualidade deste.
        </command>

        <card_content>
            {card_content}
        </card_content>

        <output_format>
            <h2>A informação está correta de acordo com fontes oficiais/acadêmicas?</h2>
            <h2>O conteúdo é coerente e bem estruturado logicamente?</h2>
            <h2>Alguma parte do conteúdo está desatualizada ou não é mais válida?</h2>
            <h2>O conteúdo pode ser simplificado ou tornar-se mais claro sem perder o significado?</h2>
            <hr>
            <h2>Veredito</h2>
                ✅ A informação é precisa e bem estruturada.
                ⚠️ Problemas menores ou margem para melhoria.
                ❌ Erros factuais encontrados que precisam de correção.
            <hr>
            <h2>Sugira quaisquer melhorias para tornar este cartão mais eficaz para o estudo.</h2>
        </output_format>

        <output_details>
            Mantenha sua explicação clara e concisa.
            Você deve responder em Português brasileiro.
            Nunca use formatação markdown ou marcadores markdown. 
            A resposta deve sempre ser formatada usando tags HTML.
            Sempre que conveniente, use listas HTML (numeradas ou com marcadores) e texto em negrito para facilitar a leitura da sua resposta.
        </output_details>   
    """,
    "es_la": """
        <command>
            Estoy estudiando con tarjetas de memoria y necesito ayuda para verificar la calidad de esta.
        </command>

        <card_content>
            {card_content}
        </card_content>

        <output_format>
            <h2>¿Es la información correcta según fuentes oficiales/académicas?</h2>
            <h2>¿Es el contenido coherente y está bien estructurado lógicamente?</h2>
            <h2>¿Alguna parte del contenido está desactualizada o ya no es válida?</h2>
            <h2>¿Se puede simplificar el contenido o hacerlo más claro sin perder el significado?</h2>
            <hr>
            <h2>Veredicto</h2>
                ✅ La información es precisa y está bien estructurada.
                ⚠️ Problemas menores o margen de mejora.
                ❌ Errores factuales encontrados que necesitan corrección.
            <hr>
            <h2>Sugiera cualquier mejora para hacer que esta tarjeta sea más efectiva para el estudio.</h2>
        </output_format>

        <output_details>
            Mantén tu explicación clara y concisa.
            Usted debe responder en español latino.
            Nunca uses formato markdown ni viñetas markdown. 
            La respuesta debe estar siempre formateada usando etiquetas HTML.
            Siempre que sea conveniente, usa listas HTML (numeradas o con viñetas) y texto en negrita para facilitar la lectura de tu respuesta.
        </output_details>   
    """,
}
