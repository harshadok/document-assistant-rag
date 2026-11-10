import 'dart:convert';
import 'dart:io';

import 'package:file_selector/file_selector.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() => runApp(const DocumentAssistant());

class DocumentAssistant extends StatelessWidget {
  const DocumentAssistant({super.key, this.client});
  final http.Client? client;
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Document Assistant',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff2457ce)),
      useMaterial3: true,
    ),
    home: LibraryScreen(client: client),
  );
}

class LibraryScreen extends StatefulWidget {
  const LibraryScreen({super.key, this.client});
  final http.Client? client;
  @override
  State<LibraryScreen> createState() => _LibraryScreenState();
}

class _LibraryScreenState extends State<LibraryScreen> {
  late final http.Client client = widget.client ?? http.Client();
  late final String baseUrl =
      const String.fromEnvironment('API_BASE_URL').isNotEmpty
      ? const String.fromEnvironment('API_BASE_URL')
      : (Platform.isAndroid ? 'http://10.0.2.2:8000' : 'http://127.0.0.1:8000');
  final question = TextEditingController();
  List<Map<String, dynamic>> documents = [];
  Map<String, dynamic>? result;
  String? selectedId, error;
  bool busy = false, generate = false;
  @override
  void initState() {
    super.initState();
    refresh();
  }

  @override
  void dispose() {
    question.dispose();
    if (widget.client == null) client.close();
    super.dispose();
  }

  dynamic decode(http.Response response) {
    final body = jsonDecode(response.body);
    if (response.statusCode >= 400) {
      final detail = body is Map ? body['detail'] : null;
      throw Exception(
        detail is String ? detail : 'Request failed. Please check your input.',
      );
    }
    return body;
  }

  Future<void> perform(Future<void> Function() action) async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await action();
    } catch (exception) {
      if (mounted) {
        setState(
          () => error = exception.toString().replaceFirst('Exception: ', ''),
        );
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> loadDocuments() async {
    final response = await client
        .get(Uri.parse('$baseUrl/documents'))
        .timeout(const Duration(seconds: 15));
    final items = (decode(response) as List).cast<Map<String, dynamic>>();
    if (mounted) {
      setState(() {
        documents = items;
        if (!items.any((d) => d['id'] == selectedId)) selectedId = null;
      });
    }
  }

  Future<void> refresh() => perform(loadDocuments);
  Future<void> upload() => perform(() async {
    final file = await openFile(
      acceptedTypeGroups: [
        const XTypeGroup(label: 'Documents', extensions: ['pdf', 'txt', 'md']),
      ],
    );
    if (file == null) return;
    if (await file.length() > 10 * 1024 * 1024) {
      throw Exception('Please choose a file smaller than 10 MB.');
    }
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/documents'),
    );
    request.files.add(
      http.MultipartFile.fromBytes(
        'file',
        await file.readAsBytes(),
        filename: file.name,
      ),
    );
    final response = await http.Response.fromStream(
      await client.send(request).timeout(const Duration(seconds: 90)),
    );
    final document = decode(response) as Map<String, dynamic>;
    await loadDocuments();
    if (mounted) {
      setState(() {
        selectedId = document['id'] as String;
        result = null;
      });
    }
  });
  Future<void> ask() => perform(() async {
    final response = await client
        .post(
          Uri.parse('$baseUrl/questions'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'question': question.text.trim(),
            'document_ids': selectedId == null ? null : [selectedId],
            'generate': generate,
          }),
        )
        .timeout(const Duration(seconds: 150));
    final answer = decode(response) as Map<String, dynamic>;
    if (mounted) setState(() => result = answer);
  });
  Future<void> remove(Map<String, dynamic> document) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete document?'),
        content: Text(
          'Remove ${document['filename']} and its searchable passages?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    await perform(() async {
      decode(
        await client
            .delete(Uri.parse('$baseUrl/documents/${document['id']}'))
            .timeout(const Duration(seconds: 15)),
      );
      if (mounted) setState(() => result = null);
      await loadDocuments();
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('Document Assistant'),
      actions: [
        IconButton(
          onPressed: busy ? null : refresh,
          icon: const Icon(Icons.refresh),
          tooltip: 'Refresh library',
        ),
      ],
    ),
    body: Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 820),
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Text(
              'Answers start with your sources.',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 8),
            const Text(
              'Upload a document, ask a question, and inspect the matching passages.',
            ),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: busy ? null : upload,
              icon: const Icon(Icons.upload_file),
              label: const Text('Upload PDF or text'),
            ),
            const SizedBox(height: 8),
            const Text(
              'Text PDFs, TXT and Markdown · up to 10 MB. Scanned PDFs are not supported.',
            ),
            if (busy)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 12),
                child: LinearProgressIndicator(),
              ),
            if (error != null)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text(
                  error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ),
            const SizedBox(height: 20),
            Text('Your library', style: Theme.of(context).textTheme.titleLarge),
            if (documents.isEmpty && !busy)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 16),
                child: Text(
                  'No documents yet. Upload your first file to get started.',
                ),
              ),
            ...documents.map(
              (d) => ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.description_outlined),
                title: Text(d['filename'] as String),
                subtitle: Text('${d['chunks']} searchable passages'),
                trailing: IconButton(
                  onPressed: busy ? null : () => remove(d),
                  icon: const Icon(Icons.delete_outline),
                  tooltip: 'Delete document',
                ),
              ),
            ),
            const SizedBox(height: 20),
            DropdownButtonFormField<String>(
              key: ValueKey(selectedId),
              initialValue: selectedId,
              decoration: const InputDecoration(
                labelText: 'Search within',
                border: OutlineInputBorder(),
              ),
              items: [
                const DropdownMenuItem<String>(
                  value: null,
                  child: Text('All documents'),
                ),
                ...documents.map(
                  (d) => DropdownMenuItem(
                    value: d['id'] as String,
                    child: Text(
                      d['filename'] as String,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ),
              ],
              onChanged: busy
                  ? null
                  : (value) => setState(() {
                      selectedId = value;
                      result = null;
                    }),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: question,
              maxLength: 2000,
              minLines: 2,
              maxLines: 4,
              decoration: const InputDecoration(
                labelText: 'Your question',
                hintText: 'How many days of annual leave are available?',
                border: OutlineInputBorder(),
              ),
              onChanged: (_) => setState(() {}),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Generate an answer with local AI'),
              subtitle: const Text(
                'Requires a configured local model. Off shows retrieved passages only.',
              ),
              value: generate,
              onChanged: busy
                  ? null
                  : (value) => setState(() {
                      generate = value;
                      result = null;
                    }),
            ),
            FilledButton(
              onPressed:
                  busy || documents.isEmpty || question.text.trim().isEmpty
                  ? null
                  : ask,
              child: const Text('Ask my documents'),
            ),
            if (result != null) ...[
              const SizedBox(height: 24),
              Text(
                result!['mode'] == 'retrieval_only'
                    ? 'Matching passages'
                    : 'Answer',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              if (result!['answer'] != null)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  child: SelectableText(result!['answer'] as String),
                ),
              if (result!['mode'] == 'retrieval_only')
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 8),
                  child: Text(
                    'These are source excerpts, not a generated answer.',
                  ),
                ),
              ...((result!['sources'] as List?) ?? []).map(
                (s) => Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${s['citation_id']} · ${s['filename']} · Page ${s['page']}',
                          style: Theme.of(context).textTheme.titleSmall,
                        ),
                        const SizedBox(height: 8),
                        SelectableText(s['text'] as String),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    ),
  );
}
