import 'package:equatable/equatable.dart';

abstract class AuthEvent extends Equatable {
  const AuthEvent();

  @override
  List<Object?> get props => [];
}

class AuthOtpSubmitted extends AuthEvent {
  final String phoneNumber;
  final String otp;

  const AuthOtpSubmitted({required this.phoneNumber, required this.otp});

  @override
  List<Object?> get props => [phoneNumber, otp];
}

class AuthSignedOut extends AuthEvent {
  const AuthSignedOut();
}
