// lib/services/storage_service.dart
import 'dart:io';
import 'package:firebase_storage/firebase_storage.dart';

class StorageService {
  StorageService._();
  static final StorageService instance = StorageService._();
  final FirebaseStorage _storage = FirebaseStorage.instance;

  Future<String> uploadUserAvatar({required String uid, required File file}) async {
    final ref = _storage.ref().child('avatars/$uid.jpg');
    final task = await ref.putFile(file, SettableMetadata(contentType: 'image/jpeg'));
    return await task.ref.getDownloadURL();
  }
}
