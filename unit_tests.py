import unittest
from unittest.mock import patch, MagicMock, mock_open, Mock
from fill_db import (
    convert_metadata, split_text, get_file_type, extract_text_from_pdf, process_file, process_paragraph,
    monitor_directory, extract_text_from_ole_doc, extract_text_from_xls,
    extract_text_from_pptx,
    NewFileHandler, extract_text_from_docx,
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

    @patch('fill_db.olefile.isOleFile')
    @patch('fill_db.olefile.OleFileIO')
    def test_extract_text_from_ole_doc(self, mock_olefileio, mock_isolefile):
        mock_isolefile.return_value = True
        mock_ole = MagicMock()
        mock_ole.exists.return_value = True
        mock_ole.openstream.return_value.read.return_value = b'Test OLE text'
        mock_olefileio.return_value = mock_ole

        result = extract_text_from_ole_doc('test.ole')
        self.assertEqual(result, [{"page_content": "Test OLE text"}])

    @patch('fill_db.olefile.isOleFile')
    @patch('fill_db.olefile.OleFileIO')
    def test_extract_text_from_ole_doc_no_worddocument(self, mock_olefileio, mock_isolefile):
        mock_isolefile.return_value = True
        mock_ole = MagicMock()
        mock_ole.exists.return_value = False
        mock_olefileio.return_value = mock_ole

        result = extract_text_from_ole_doc('test.ole')
        self.assertEqual(result, [])

    @patch('fill_db.Document')
    def test_extract_text_from_docx(self, mock_document):
        mock_doc = MagicMock()
        mock_paragraph = MagicMock()
        mock_paragraph.text = 'Test DOCX text'
        mock_doc.paragraphs = [mock_paragraph]
        mock_document.return_value = mock_doc

        result = extract_text_from_docx('test.docx')
        self.assertEqual(result, [{"page_content": 'Test DOCX text'}])

    @patch('fill_db.Document')
    def test_extract_text_from_docx_empty(self, mock_document):
        mock_doc = MagicMock()
        mock_paragraph = MagicMock()
        mock_paragraph.text = ''
        mock_doc.paragraphs = [mock_paragraph]
        mock_document.return_value = mock_doc

        result = extract_text_from_docx('empty.docx')
        self.assertEqual(result, [])

    @patch('fill_db.Document')
    def test_extract_text_from_docx_error(self, mock_document):
        mock_document.side_effect = Exception("Error opening file")
        result = extract_text_from_docx('error.docx')
        self.assertEqual(result, [])

    @patch('fill_db.xlrd.open_workbook')
    def test_extract_text_from_xls(self, mock_open_workbook):
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_sheet.nrows = 2
        mock_sheet.row_values.side_effect = [['A', 'B'], [1, 2]]
        mock_open_workbook.return_value.sheet_by_index.return_value = mock_sheet

        result = extract_text_from_xls('test.xls')
        self.assertEqual(result, [{"page_content": "['A', 'B']\n[1, 2]"}])

    @patch('fill_db.xlrd.open_workbook')
    def test_extract_text_from_xls_empty(self, mock_open_workbook):
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_sheet.nrows = 0
        mock_open_workbook.return_value.sheet_by_index.return_value = mock_sheet

        result = extract_text_from_xls('empty.xls')
        self.assertEqual(result, [])

    @patch('fill_db.xlrd.open_workbook')
    def test_extract_text_from_xls_error(self, mock_open_workbook):
        mock_open_workbook.side_effect = Exception("Error opening file")
        result = extract_text_from_xls('error.xls')
        self.assertEqual(result, [])

    @patch('fill_db.Presentation')
    def test_extract_text_from_pptx(self, mock_presentation):
        mock_prs = MagicMock()
        mock_slide = MagicMock()
        mock_shape = MagicMock()
        mock_shape.text = 'Test text from PPT/PPTX'
        mock_slide.shapes = [mock_shape]
        mock_prs.slides = [mock_slide]
        mock_presentation.return_value = mock_prs
        result = extract_text_from_pptx('test.pptx')
        self.assertEqual(result, [{"page_content": 'Test text from PPT/PPTX'}])

    @patch('fill_db.Presentation')
    def test_extract_text_from_pptx_empty(self, mock_presentation):
        mock_prs = MagicMock()
        mock_prs.slides = []
        mock_presentation.return_value = mock_prs
        result = extract_text_from_pptx('empty.pptx')
        self.assertEqual(result, [{"page_content": ""}])

    @patch('fill_db.Presentation')
    def test_extract_text_from_pptx_error(self, mock_presentation):
        mock_presentation.side_effect = Exception("Error opening file")
        result = extract_text_from_pptx('error.pptx')
        self.assertEqual(result, [])

    @patch('os.path.exists', return_value=True)
    @patch('utils.calculate_file_hash', return_value='fake_hash')
    @patch('fill_db.MongoDB')
    @patch('fill_db.extract_text_from_pdf')
    @patch('fill_db.extract_text_from_docx')
    @patch('fill_db.extract_text_from_ole_doc')
    @patch('fill_db.extract_text_from_xlsx')
    @patch('fill_db.extract_text_from_xls')
    @patch('fill_db.extract_text_from_pptx')
    @patch('fill_db.extract_text_from_txt')
    def test_process_file(self, mock_txt, mock_pptx, mock_xls, mock_xlsx,
                          mock_ole_doc, mock_docx, mock_pdf, mock_db,
                          mock_hash, mock_exists):
        # Setup mock database
        mock_db_instance = Mock()
        mock_db_instance.query_documents.return_value = []  # No existing documents
        mock_db.return_value = mock_db_instance

        # Setup mocks for each file type
        mock_pdf.return_value = [{"page_content": 'Test PDF'}]
        mock_docx.return_value = [{"page_content": 'Test DOCX'}]
        mock_ole_doc.return_value = [{"page_content": 'Test DOC'}]
        mock_xlsx.return_value = [{"page_content": 'Test XLSX'}]
        mock_xls.return_value = [{"page_content": 'Test XLS'}]
        mock_pptx.return_value = [{"page_content": 'Test PPT'}]
        mock_txt.return_value = [{"page_content": 'Test TXT'}]

        # Test cases
        test_cases = [
            ('test.pdf', 'application/pdf', mock_pdf),
            ('test.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', mock_docx),
            ('test.doc', 'application/msword', mock_ole_doc),
            ('test.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', mock_xlsx),
            ('test.xls', 'application/vnd.ms-excel', mock_xls),
            ('test.pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', mock_pptx),
            ('test.txt', 'text/plain', mock_txt),
        ]

        for file_path, file_type, mock_func in test_cases:
            with self.subTest(file_path=file_path):
                # Reset all mocks
                mock_exists.reset_mock()
                mock_hash.reset_mock()
                mock_db_instance.query_documents.reset_mock()
                mock_func.reset_mock()

                # Call the function
                result = process_file(file_path, file_type)

                # Assertions
                self.assertEqual(result, mock_func.return_value)

                # Verify all mocks were called
                mock_exists.assert_called_once_with(file_path)
                mock_hash.assert_called_once_with(file_path)
                mock_db_instance.query_documents.assert_called_once_with("data", {"metadata.file_hash": 'fake_hash'})
                mock_func.assert_called_once_with(file_path)

        # Test case for unsupported file type
        result = process_file('test.unsupported', 'application/unsupported')
        self.assertEqual(result, [])

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
