import re

from ingest.importer.conversion import template_manager
from ingest.importer.conversion.template_manager import TemplateManager
from ingest.importer.data_node import DataNode
from ingest.importer.spreadsheet.ingest_workbook import IngestWorkbook


class WorkbookImporter:

    def __init__(self):
        self.worksheet_importer = WorksheetImporter()

    def do_import(self, workbook: IngestWorkbook):
        pre_ingest_json_list = []
        tm = template_manager.build(workbook.get_schemas())
        for worksheet in workbook.importable_worksheets():
            json_list = self.worksheet_importer.do_import(worksheet, tm)
            pre_ingest_json_list.extend(json_list)
        return pre_ingest_json_list


class WorksheetImporter:

    def __init__(self):
        pass

    def do_import(self, worksheet, template:TemplateManager, entity):
        json_list = []
        for row in self._get_data_rows(worksheet):
            node = template.create_template_node(worksheet)
            ontology_tracker = OntologyTracker()
            for cell in row:
                # TODO preprocess headers so that cells can be converted without having to always
                # check the header
                header_name = self._get_header_name(cell, worksheet)

                cell_value = cell.value
                field_chain = self._get_field_chain(header_name)

                if cell_value is None:
                    continue

                if template.is_ontology_subfield(header_name):
                    ontology_tracker.track_value(field_chain, cell_value)
                    continue

                converter = template.get_converter(header_name)
                data = converter.convert(cell_value)
                node[field_chain] = data

            ontology_fields = ontology_tracker.get_ontology_fields()
            for field_chain in ontology_fields:
                node[field_chain] = ontology_tracker.get_value_by_field(field_chain)

            json_list.append(node.as_dict())

        return json_list

    def _get_data_rows(self, worksheet):
        return worksheet.iter_rows(row_offset=3, max_row=(worksheet.max_row - 3))

    def _get_header_name(self, cell, worksheet):
        header_coordinate = '%s1' % (cell.column)
        return worksheet[header_coordinate].value

    def _get_field_chain(self, header_name):
        match = re.search('(\w+\.){1}(?P<field_chain>.*)', header_name)
        return match.group('field_chain')


class OntologyTracker(object):

    def __init__(self):
        self.ontology_values = {}

    def _get_ontology_field(self, field_chain):
        match = re.search('(?P<field_chain>.*)(\.\w+)', field_chain)
        return match.group('field_chain')

    def _get_ontology_subfield(self, field_chain):
        match = re.search('(.*)\.(?P<field>\w+)', field_chain)
        return match.group('field')

    def track_value(self, header_name, value):
        ontology_subfield = self._get_ontology_subfield(header_name)
        ontology_field = self._get_ontology_field(header_name)

        if not self.ontology_values.get(ontology_field):
            self.ontology_values[ontology_field] = {}

        self.ontology_values[ontology_field][ontology_subfield] = value

    def get_ontology_fields(self):
        return self.ontology_values.keys()

    def get_value_by_field(self, field):
        return [self.ontology_values[field]]