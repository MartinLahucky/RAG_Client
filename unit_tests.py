import pandas as pd
import unittest
from unittest.mock import patch, MagicMock

import pandas as pd

from fill_db import (
    convert_metadata, split_text, get_file_type, extract_text_from_pdf,
    extract_text_from_docx, extract_text_from_pptx, extract_text_from_xlsx,
    process_file, process_paragraph, monitor_directory, NewFileHandler
)


class TestFileFunctions(unittest.TestCase):


    def test_convert_metadata(self):
        metadata = {
            'list': [1, 2, 3],
            'string': 'test',
            'int': 1,
            'float': 1.0,
            'bool': True,
            'complex': complex(1, 2),
            'tokens': ['Test', 'text'],
            'pos_tags': [('Test', 'NN'), ('text', 'NN')],
            'named_entities': [('Test', 'ORG')]
        }
        result = convert_metadata(metadata)

        self.assertEqual(result['list'], '[1, 2, 3]')
        self.assertEqual(result['string'], 'test')
        self.assertEqual(result['int'], 1)
        self.assertEqual(result['float'], 1.0)
        self.assertEqual(result['bool'], True)
        self.assertEqual(result['complex'], '(1+2j)')
        self.assertEqual(result['tokens'], ['Test', 'text'])
        self.assertEqual(result['pos_tags'], [('Test', 'NN'), ('text', 'NN')])
        self.assertEqual(result['named_entities'], [('Test', 'ORG')])

    @patch('magic.Magic')
    def test_get_file_type(self, mock_magic):
        mock_magic.return_value.from_file.return_value = 'application/pdf'
        self.assertEqual(get_file_type('test.pdf'), 'application/pdf')

        mock_magic.return_value.from_file.return_value = 'application/octet-stream'
        self.assertEqual(get_file_type('test.docx'),
                         'application/vnd.openxmlformats-officedocument.wordprocessingml.document')

    @patch('fitz.open')
    def test_extract_text_from_pdf(self, mock_fitz_open):
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = 'Test text'
        mock_doc.__iter__.return_value = [mock_page]
        mock_fitz_open.return_value = mock_doc

        result = extract_text_from_pdf('test.pdf')
        self.assertEqual(result, [{"page_content": 'Test text'}])

    @patch('docx.Document')
    def test_extract_text_from_docx(self, mock_document):
        mock_doc = MagicMock()
        mock_para = MagicMock()
        mock_para.text = 'Test text'
        mock_doc.paragraphs = [mock_para]
        mock_document.return_value = mock_doc

        result = extract_text_from_docx('test.docx')
        self.assertEqual(result, [{"page_content": 'Test text'}])

    @patch('pptx.Presentation')
    def test_extract_text_from_pptx(self, mock_presentation):
        mock_prs = MagicMock()
        mock_slide = MagicMock()
        mock_shape = MagicMock()
        mock_shape.text = 'Test text'
        mock_slide.shapes = [mock_shape]
        mock_prs.slides = [mock_slide]
        mock_presentation.return_value = mock_prs

        result = extract_text_from_pptx('test.pptx')
        self.assertEqual(result, [{"page_content": 'Test text'}])

    @patch('pandas.read_excel')
    def test_extract_text_from_xlsx(self, mock_read_excel):
        mock_df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        mock_read_excel.return_value = mock_df

        result = extract_text_from_xlsx('test.xlsx')
        self.assertEqual(result, [{"page_content": " A  B\n 1  3\n 2  4"}])

    @patch('fill_db.extract_text_from_pdf')
    @patch('fill_db.extract_text_from_docx')
    @patch('fill_db.extract_text_from_pptx')
    @patch('fill_db.extract_text_from_xlsx')
    @patch('fill_db.extract_text_from_txt')
    @patch('os.path.exists')
    def test_process_file(self, mock_exists, mock_txt, mock_xlsx, mock_pptx, mock_docx, mock_pdf):
        mock_exists.return_value = True
        mock_pdf.return_value = [{"page_content": "PDF content"}]
        mock_docx.return_value = [{"page_content": "DOCX content"}]
        mock_pptx.return_value = [{"page_content": "PPTX content"}]
        mock_xlsx.return_value = [{"page_content": "XLSX content"}]
        mock_txt.return_value = [{"page_content": "TXT content"}]

        self.assertEqual(process_file('test.pdf', 'application/pdf'), [{"page_content": "PDF content"}])
        self.assertEqual(
            process_file('test.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
            [{"page_content": "DOCX content"}])
        self.assertEqual(
            process_file('test.pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation'),
            [{"page_content": "PPTX content"}])
        self.assertEqual(
            process_file('test.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            [{"page_content": "XLSX content"}])
        self.assertEqual(process_file('test.txt', 'text/plain'), [{"page_content": "TXT content"}])

        # Test for unsupported file type
        self.assertEqual(process_file('test.unknown', 'application/unknown'), [])

        # Test for file not found
        mock_exists.return_value = False
        self.assertEqual(process_file('nonexistent.pdf', 'application/pdf'), [])

    @patch('fill_db.tokenizer')
    def test_process_paragraph(self, mock_tokenizer):
        mock_tokenizer.tokenize_text.return_value = ['Test', 'text']
        mock_tokenizer.pos_tag.return_value = [('Test', 'NN'), ('text', 'NN')]
        mock_tokenizer.named_entity_recognition.return_value = [('Test', 'ORG')]

        paragraph = {"page_content": "Test text", "page": 1}
        result = process_paragraph(paragraph, 'test.pdf')

        print("Result:", result)
        print("Tokens type:", type(result['metadata']['tokens']))
        print("Tokens value:", result['metadata']['tokens'])

        self.assertEqual(result['content'], "Test text")
        self.assertIsInstance(result['metadata']['tokens'], list)
        self.assertEqual(result['metadata']['tokens'], ['Test', 'text'])
        self.assertIsInstance(result['metadata']['pos_tags'], list)
        self.assertEqual(result['metadata']['pos_tags'], [('Test', 'NN'), ('text', 'NN')])
        self.assertIsInstance(result['metadata']['named_entities'], list)
        self.assertEqual(result['metadata']['named_entities'], [('Test', 'ORG')])
        self.assertEqual(result['metadata']['source'], 'test.pdf')
        self.assertEqual(result['metadata']['page'], 1)

        # Test with missing 'page' in input
        paragraph_no_page = {"page_content": "Test text"}
        result_no_page = process_paragraph(paragraph_no_page, 'test_no_page.pdf')

        self.assertEqual(result_no_page['content'], "Test text")
        self.assertIsInstance(result_no_page['metadata']['tokens'], list)
        self.assertEqual(result_no_page['metadata']['tokens'], ['Test', 'text'])
        self.assertIsInstance(result_no_page['metadata']['pos_tags'], list)
        self.assertEqual(result_no_page['metadata']['pos_tags'], [('Test', 'NN'), ('text', 'NN')])
        self.assertIsInstance(result_no_page['metadata']['named_entities'], list)
        self.assertEqual(result_no_page['metadata']['named_entities'], [('Test', 'ORG')])
        self.assertEqual(result_no_page['metadata']['source'], 'test_no_page.pdf')
        self.assertEqual(result_no_page['metadata']['page'], 0)  # Should default to 0

    def test_split_text(self):
        raw_documents = [
            "This is a test. It has multiple sentences! How many? Three. And it's longer than 100 characters to ensure multiple chunks."]
        result = split_text(raw_documents)

        # Check that we have at least 2 chunks due to the length
        self.assertGreater(len(result), 1)

        # Check that each chunk is a dictionary with 'page_content'
        for chunk in result:
            self.assertIsInstance(chunk, dict)
            self.assertIn('page_content', chunk)

        # Check that when combined, the chunks contain all the original text
        combined_text = ' '.join([chunk['page_content'] for chunk in result])
        self.assertEqual(combined_text.replace(' ', ''), raw_documents[0].replace(' ', ''))

        # Test with dictionary input
        raw_documents_dict = [{"page_content": "This is another test. With two sentences."}]
        result_dict = split_text(raw_documents_dict)
        self.assertGreater(len(result_dict), 0)
        self.assertIsInstance(result_dict[0], dict)
        self.assertIn('page_content', result_dict[0])

class TestNewFileHandler(unittest.TestCase):
    @patch('fill_db.logger')
    def test_on_created(self, mock_logger):
        mock_process_function = MagicMock()
        handler = NewFileHandler(mock_process_function)

        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = '/path/to/new/file.txt'

        handler.on_created(mock_event)

        mock_logger.log_info.assert_called_once_with("Nový soubor detekován: /path/to/new/file.txt")
        mock_process_function.assert_called_once()

    @patch('fill_db.logger')
    def test_on_created_directory(self, mock_logger):
        mock_process_function = MagicMock()
        handler = NewFileHandler(mock_process_function)

        mock_event = MagicMock()
        mock_event.is_directory = True
        mock_event.src_path = '/path/to/new/directory'

        handler.on_created(mock_event)

        mock_logger.log_info.assert_not_called()
        mock_process_function.assert_not_called()


class TestMonitorDirectory(unittest.TestCase):
    @patch('fill_db.Observer')
    @patch('fill_db.NewFileHandler')
    @patch('fill_db.time.sleep', side_effect=KeyboardInterrupt)
    def test_monitor_directory(self, mock_sleep, mock_handler, mock_observer):
        mock_process_function = MagicMock()

        monitor_directory('test_directory', mock_process_function)

        mock_handler.assert_called_once_with(mock_process_function)
        mock_observer.return_value.schedule.assert_called_once()
        mock_observer.return_value.start.assert_called_once()
        mock_observer.return_value.stop.assert_called_once()
        mock_observer.return_value.join.assert_called_once()


class TestLoadAndProcessDocuments(unittest.TestCase):
    @patch('fill_db.MongoDB')
    @patch('fill_db.os.walk')
    @patch('fill_db.get_file_type')
    @patch('fill_db.process_file')
    @patch('fill_db.split_text')
    @patch('fill_db.process_paragraph')
    @patch('fill_db.logger')
    def test_load_and_process_documents(self, mock_logger, mock_process_paragraph, mock_split_text,
                                        mock_process_file, mock_get_file_type, mock_walk, mock_mongodb):
        mock_db = MagicMock()
        mock_mongodb.return_value = mock_db

        mock_walk.return_value = [
            ('/fake/path', [], ['file1.pdf', 'file2.docx'])
        ]

        mock_get_file_type.side
