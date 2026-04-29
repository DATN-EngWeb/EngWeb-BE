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
        "Return JSON with keys: translation, literal_translation, word_or_phrase, explanation, english_tip."
        "- `word_or_phrase`: an object mapping phrases to meanings/explanations\n"
        "- `explanation`: a detailed explanation for the whole translated sentence\n"
        "- `english_tip`: a learning tip related to the whole translated sentence\n"
        "4. If a key is not needed, omit it. Do not add extra keys.\n"
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
        "Return JSON with keys: grammar_point, explanation, examples, common_mistakes, english_tip."
        "6. If a key is not needed, omit it. Do not add extra keys.\n"
    ),
    AssistantConversation.MODE_VOCABULARY: (
        "Mode: vocabulary\n"
        "User request: {message}\n\n"
        "Requirements:\n"
        "1. Explain meaning in context.\n"
        "2. Add pronunciation tip if useful.\n"
        "3. Provide collocations and synonyms/antonyms when relevant.\n"
        "4. Provide examples appropriate for user level.\n"
        "Return JSON with keys: meaning, pronunciation_tip, collocations, synonyms, antonyms, examples."
        "- `collocations`, `synonyms`, `antonyms` are arrays of strings with translations (e.g., 'phrase 1 (translation)', 'phrase 2 (translation)').\n"
        "5. If a key is not needed, omit it. Do not add extra keys.\n"
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
        "Return valid JSON only with keys: ideas, outline, useful_vocabulary, linking_words, sample_thesis, topic_sentences.\n"
        "- `ideas`: a list of objects, each with 'subtopic' (string) and 'points' (array of strings). "
        "- `outline`: a suggested outline for writing about the topic, with 'introduction', 'body', and 'conclusion' sections. Each section is an array of strings representing main points. "
        "- `useful_vocabulary`: a list of useful words/phrases with translations (e.g., 'phrase 1 (translation)', 'phrase 2 (translation)'). "
        "- `linking_words`: a list of linking words/phrases with translations (e.g., 'however (translation)', 'in addition (translation)')."
        "- `sample_thesis`: a sample thesis statement (string).\n"
        "- `topic_sentences`: an array of sample topic sentences (array of strings).\n"
        "7. If a key is not needed, omit it. Do not add extra keys.\n"
        "8. Content should be in English to support English writing practice.\n"
    ),
    AssistantConversation.MODE_GENERAL: (
        "Mode: general\n"
        "User question: {message}\n\n"
        "Requirements:\n"
        "1. Answer concisely and accurately.\n"
        "2. Use a short answer plus key points.\n"
        "3. If the user asks to learn English from the topic, include an optional English learning tip.\n"
        "4. Do not produce unsafe or policy-violating content.\n"
        "Return JSON with keys: answer, key_points.\n"
        "- `answer`: a concise answer to the user's question (string).\n"
        "- `key_points`: an array of key points to highlight (array of strings).\n"
    ),
}
