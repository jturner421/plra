"""
Set of methods to extract information from PDF filee and convert to Panda dataframe.
"""
import collections
import PyPDF2
import camelot
import pandas as pd

PdfInformation = collections.namedtuple('PdfInformation', 'txtvalue, numpg')


def extract_pdf_header(input_files):
    """
    Extracts information (check number, amount) from left hand side of the state check detail PDF
    :param input_files: file name to process
    :return: dataframe of header information
    """
    header_block = camelot.read_pdf(input_files, flavor='stream', pages='1', table_areas=['50,541,249,469'],
                                    columns=['26,105'], split_text=True)
    try:
        print('Extracting header information\n')
        header = header_block[0].df
        return header
    except:
        print(f"Can not read header area for {input_files}.  Please check your PDF document.")
        print('Exiting program')
        exit(1)


def extract_pdf_table_information_first_page(input_files, pages):
    """
        Takes a text based PDF image, extracts text from first page pre-defined region and creates a dataframe.
        :param input_files: Name of file to process
        :param pages: number of pages of PDF
        :return: dataframe of payees
        """
    tables = camelot.read_pdf(input_files, flavor='stream', pages='1', table_areas=['74,455,768,30'],
                              columns=['73,113,267,324,550,730'], row_tol=10, split_text=True)

    page1_converted = False
    while not page1_converted:
        print(f"Extracting page 1\n")
        # Ignores first page of scan and extracts information from Page 2 which has a different format than
        # subsequent pages
        dframe = tables[0].df  # creates dataframe from first page of scan
        dframe = column_extraction_cleanup(dframe)
        page1_converted = True
    return dframe

# noinspection PyPep8Naming
def extract_PDF_table_information_remaining_pages(input_files, pages):
    """
    Takes a text based PDF image, extracts text from pre-defined region or PDF files with more than two pages
    and creates a dataframe.

    :param input_files: Name of file to process
    :param pages: number of pages of PDF
    :return: dataframe of payees
    """
    print("Extracting rest of document\n")
    dframe_dict = {}
    end_range = pages + 1
    page_errors = []
    for i in range(2,end_range ):
        try:
            print(f'Extracting page #{i}')
            tables1 = _process_pdf_page(input_files, i)
            dframe = tables1[0].df
            # drop first three rows as they contain header information that can cause a miscount when processing
            dframe= dframe.drop(dframe.index[[0, 2]])
            dframe = column_extraction_cleanup(dframe)
            dframe_dict[i] = dframe
        #capture pages not processed
        except IndexError:
            print(f'Page {i} encountered an error while processing')
            page_errors.append(i)
            pass
    dframe1 = pd.concat(dframe_dict.values())
    return dframe1, page_errors


def _process_pdf_page(input_file, page_num):
    """
    Helper function that extracts text from single PDF page and creates dataframe
    :param input_file: PDF to be processed
    :param page_num: page number to process
    :return: dataframe
    """
    tables1 = camelot.read_pdf(input_file, flavor='stream', pages=str(page_num), columns=['73,113,267,324,550,730'],
                               row_tol=10, split_text=True)
    return tables1


def check_for_null_amounts(dframe):
    """
    Checks for empty strings and deletes row from dataframe
    :param dframe:
    :return: dataframe
    """
    print(f"Checking for non numeric values in Amount Column\n")
    # Check for empty strings in amount
    s = dframe['Amount'].str.match('^\$(\d{1,3}(\,\d{3})*|(\d+))(\.\d{2})?$')
    for i, val in s.iteritems():
        if not val:
            dframe = dframe.drop(i)
            print(f"Deleting row {i} as it contains non numeric data\n")
    return dframe


def delete_header_row(dframe):
    """
    Checks to see if column header from PDF is in first row and removes it
    :param dframe
    :return: dframe
    """
    check_for_non_num = dframe.iloc[0:1]
    check_for_non_num_val = check_for_non_num['DOC'].item()
    if check_for_non_num_val == 'DOC #':
        dframe = dframe.drop(0)

    return dframe


def column_extraction_cleanup(dframe):
    """
    Deletes extraneous columns captured during PDF conversion
    :param dframe:
    :return: dataframe with relevant columns
    """
    # Todo: refactor and cleanup code duplication
    col_nums = dframe.shape[1]


    if col_nums == 7:
        # subset columns 1,2, & 6
        dframe = dframe[[1, 2, 5, 6]]
        dframe.columns = ['DOC', 'Name', 'Case_Notes','Amount']
        dframe = delete_header_row(dframe)
        dframe = check_for_null_amounts(dframe)
        return dframe
    elif col_nums == 4:
        # subset columns 1,2, & 6
        dframe = dframe[[0, 1, 3]]
        dframe.columns = ['DOC', 'Name', 'Amount']
        dframe = delete_header_row(dframe)
        return dframe
    elif col_nums == 5:
        # subset columns 1,2, & 6
        dframe = dframe[[0, 1, 4]]
        dframe.columns = ['DOC', 'Name', 'Amount']
        dframe = delete_header_row(dframe)
        return dframe
    else:
        return dframe


def check_pdf_for_text(file):
    """
    The function checks if a PDF is an image or text base by attempting to extract text from the first page of a PDF
    :type file: str
    :param file: PDF file path and name
    :return: True if text or False if empty string, number of pages for PDF file
    """

    pdf = PyPDF2.PdfFileReader(file)
    page = pdf.getPage(0)
    text = page.extractText()
    num_pages = pdf.getNumPages()
    if not text:
        istext = False
        info = PdfInformation(txtvalue=istext, numpg=num_pages)
    else:
        istext = True
        info = PdfInformation(txtvalue=istext, numpg=num_pages)
    return info
