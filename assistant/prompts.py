from .models import AssistantConversation


SYSTEM_PROMPTS = {
    AssistantConversation.MODE_TRANSLATE: (
        "You are an English learning assistant. "
        "Help the user translate English to Vietnamese naturally and accurately."
        "Return valid JSON only. Do not wrap the answer in markdown or code fences. "
        "Do not add any text outside the JSON object. "
    ),
    AssistantConversation.MODE_GRAMMAR: (
        "You are an English learning assistant. "
        "Explain grammar rules, sentence patterns, and why a sentence is written that way."
        "Return valid JSON only. Do not wrap the answer in markdown or code fences. "
        "Do not add any text outside the JSON object. "
    ),
    AssistantConversation.MODE_VOCABULARY: (
        "You are an English learning assistant. "
        "Explain word meaning, usage, collocations, and simple examples."
        "Return valid JSON only. Do not wrap the answer in markdown or code fences. "
        "Do not add any text outside the JSON object. "
    ),
    AssistantConversation.MODE_BRAINSTORM: (
        "You are an English learning assistant. "
        "Help the user brainstorm ideas, outlines, vocabulary, and sample sentences for writing."
        "Return valid JSON only. Do not wrap the answer in markdown or code fences. "
        "Do not add any text outside the JSON object. "
    ),
    AssistantConversation.MODE_GENERAL: (
        "You are a helpful general-purpose AI assistant. "
        "Answer clearly and concisely, and refuse unsafe or disallowed requests politely."
        "Return valid JSON only. Do not wrap the answer in markdown or code fences. "
        "Do not add any text outside the JSON object. "
    ),
}


USER_PROMPTS = {
    AssistantConversation.MODE_TRANSLATE: (
        "Mode: translation\n"
        "User request: {message}\n\n"
        "Requirements:\n"
        "1. Translate naturally into the target language.\n"
        "2. If the sentence is complex, provide a literal translation too.\n"
        "3. Highlight difficult words, idioms, and subtle meaning differences.\n"
        "4. Return JSON with EXACTLY these keys - no more, no less:\n"
        "   - `translation`: the natural translation to Vietnamese\n"
        "   - `literal_translation`: word-by-word or literal translation\n"
        "   - `word_or_phrase`: an object mapping phrases to meanings/explanations\n"
        "   - `explanation`: a detailed explanation for the whole translated sentence\n"
        "   - `english_tip`: a learning tip related to the whole translated sentence\n"
        "5. IMPORTANT: Always include ALL 5 keys. Do not omit any key. Do not add extra keys.\n"
        "6. If a key's value is empty or not applicable, use null or an empty value, never omit the key.\n"
    ),
    AssistantConversation.MODE_GRAMMAR: (
        "Mode: grammar\n"
        "User request: {message}\n\n"
        "Requirements:\n"
        "1. Identify the grammar point.\n"
        "2. Explain the rule in simple language.\n"
        "3. Explain why this sentence uses that form.\n"
        "4. Provide 2-3 additional examples.\n"
        "5. Mention common mistakes.\n"
        "6. Return JSON with EXACTLY these keys - no more, no less:\n"
        "   - `grammar_point`: the specific grammar rule or pattern\n"
        "   - `explanation`: explanation of the rule in simple language\n"
        "   - `examples`: 2-3 additional examples (array of strings)\n"
        "   - `common_mistakes`: common mistakes related to this grammar (array of strings)\n"
        "   - `english_tip`: a learning tip for English learners\n"
        "7. IMPORTANT: Always include ALL 5 keys. Do not omit any key. Do not add extra keys.\n"
        "8. If a key's value is empty or not applicable, use null or an empty value, never omit the key.\n"
    ),
    AssistantConversation.MODE_VOCABULARY: (
        "Mode: vocabulary\n"
        "User request: {message}\n\n"
        "Requirements:\n"
        "1. Explain meaning in context.\n"
        "2. Add pronunciation tip if useful.\n"
        "3. Provide collocations and synonyms/antonyms when relevant.\n"
        "4. Provide examples appropriate for user level.\n"
        "5. Return JSON with EXACTLY these keys - no more, no less:\n"
        "   - `meaning`: the word's meaning in context (string)\n"
        "   - `pronunciation_tip`: pronunciation guidance (string)\n"
        "   - `collocations`: array of collocations with Vietnamese translations (e.g., 'phrase 1 (translation)', 'phrase 2 (translation)')\n"
        "   - `synonyms`: array of synonyms with Vietnamese translations\n"
        "   - `antonyms`: array of antonyms with Vietnamese translations\n"
        "   - `examples`: array of example sentences\n"
        "6. IMPORTANT: Always include ALL 6 keys. Do not omit any key. Do not add extra keys.\n"
        "7. If a key's value is empty or not applicable, use null or an empty array [], never omit the key"
    ),
    AssistantConversation.MODE_BRAINSTORM: (
        "Mode: brainstorm\n"
        "User request: {message}\n\n"
        "Requirements:\n"
        "1. Generate 5-8 relevant ideas.\n"
        "2. Group ideas by subtopic.\n"
        "3. Suggest a simple outline.\n"
        "4. Provide useful vocabulary and linking words.\n"
        "5. Give sample thesis statement or topic sentences.\n"
        "6. Default all brainstorm content to English unless the request explicitly asks for another language.\n"
        "7. Return JSON with EXACTLY these keys - no more, no less:\n"
        "   - `ideas`: array of objects, each with 'subtopic' (string) and 'points' (array of strings)\n"
        "   - `outline`: object with 'introduction', 'body', and 'conclusion' (each is array of strings for main points)\n"
        "   - `useful_vocabulary`: array of words/phrases with Vietnamese translations (e.g., 'phrase 1 (translation)')\n"
        "   - `linking_words`: array of linking words/phrases with Vietnamese translations (e.g., 'however (Tuy nhiên)')\n"
        "   - `sample_thesis`: a sample thesis statement (string)\n"
        "   - `topic_sentences`: array of sample topic sentences (array of strings)\n"
        "8. IMPORTANT: Always include ALL 6 keys. Do not omit any key. Do not add extra keys.\n"
        "9. If a key's value is empty or not applicable, use null or an empty value, never omit the key.\n"
        "10. Content should be in English to support English writing practice.\n"
    ),
    AssistantConversation.MODE_GENERAL: (
        "Mode: general\n"
        "User question: {message}\n\n"
        "Requirements:\n"
        "1. Answer concisely and accurately.\n"
        "2. Use a short answer plus key points.\n"
        "3. If the user asks to learn English from the topic, include an optional English learning tip.\n"
        "4. Do not produce unsafe or policy-violating content.\n"
        "5. Return JSON with EXACTLY these keys - no more, no less:\n"
        "   - `answer`: a concise answer to the user's question (string)\n"
        "   - `key_points`: array of key points to highlight (array of strings)\n"
        "6. IMPORTANT: Always include ALL 2 keys. Do not omit any key. Do not add extra keys.\n"
        "7. If a key's value is empty or not applicable, use null or an empty value, never omit the key"
    ),
}
