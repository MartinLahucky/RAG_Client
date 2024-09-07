import argparse
import json
import ssl
import nltk
import os


def setup_ssl():
    ssl._create_default_https_context = ssl._create_unverified_context


def download_nltk_data():
    resources = ['punkt', 'averaged_perceptron_tagger', 'maxent_ne_chunker', 'words', 'punkt_tab',
                 'averaged_perceptron_tagger_eng', 'maxent_ne_chunker_tab']
    for resource in resources:
        try:
            nltk.data.find(f'tokenizers/{resource}')
        except LookupError:
            print(f"Downloading {resource}...")
            nltk.download(resource, quiet=True)
        else:
            print(f"{resource} is already downloaded.")


def tokenize_text(text, language='english'):
    if language == 'czech':
        return nltk.word_tokenize(text, language='czech')
    return nltk.word_tokenize(text)


def pos_tag(tokens, language='english'):
    return nltk.pos_tag(tokens)


def named_entity_recognition(tagged_tokens):
    return nltk.ne_chunk(tagged_tokens)


def process_text(text, language='english'):
    tokens = tokenize_text(text, language)
    tagged = pos_tag(tokens, language)
    ner = named_entity_recognition(tagged)
    return {
        'tokens': tokens,
        'pos_tags': tagged,
        'named_entities': str(ner)
    }


def save_results(results, output_format='json', output_folder='outputs', output_file='output'):
    os.makedirs(output_folder, exist_ok=True)
    file_path = os.path.join(output_folder, f'{output_file}.{output_format}')

    if output_format == 'json':
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    elif output_format == 'txt':
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(str(results))
    print(f"Results saved to {file_path}")


def main():
    setup_ssl()
    download_nltk_data()

    parser = argparse.ArgumentParser(description="NLP processing with NLTK")
    parser.add_argument("--text", type=str, help="Text to process")
    parser.add_argument("--file", type=str, help="File containing text to process")
    parser.add_argument("--language", type=str, default="english", choices=["english", "czech"],
                        help="Language of the text")
    parser.add_argument("--output_folder", type=str, default="outputs", help="Output folder for saving results")
    parser.add_argument("--output", type=str, default="output", help="Output file name")
    parser.add_argument("--format", type=str, default="json", choices=["json", "txt"], help="Output format")
    args = parser.parse_args()

    if args.text:
        text = args.text
    elif args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        text = input("Enter the text to process: ")

    results = process_text(text, args.language)
    save_results(results, args.format, args.output_folder, args.output)
    print("Processing complete. Results saved.")


if __name__ == "__main__":
    main()
