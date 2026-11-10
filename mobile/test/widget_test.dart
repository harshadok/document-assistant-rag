import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:document_assistant/main.dart';

void main() {
  testWidgets('shows retrieved evidence without claiming answer generation', (
    tester,
  ) async {
    final client = MockClient((request) async {
      if (request.method == 'GET') {
        return http.Response(
          jsonEncode([
            {'id': 'doc1', 'filename': 'policy.txt', 'chunks': 1},
          ]),
          200,
        );
      }
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['question'], 'How much leave?');
      expect(body['generate'], false);
      return http.Response(
        jsonEncode({
          'mode': 'retrieval_only',
          'answer': null,
          'citations': [],
          'sources': [
            {
              'citation_id': 'S1',
              'filename': 'policy.txt',
              'page': 1,
              'text': 'Annual leave is 24 days.',
            },
          ],
        }),
        200,
      );
    });
    await tester.pumpWidget(DocumentAssistant(client: client));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'How much leave?');
    await tester.scrollUntilVisible(
      find.text('Ask my documents'),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.text('Ask my documents'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('Matching passages'),
      150,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Matching passages'), findsOneWidget);
    expect(find.text('S1 · policy.txt · Page 1'), findsOneWidget);
    expect(find.text('Annual leave is 24 days.'), findsOneWidget);
  });
}
