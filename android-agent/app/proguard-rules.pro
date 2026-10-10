# ARES Android Agent ProGuard / R8 Rules

# Preserve serialization models
-keepattributes *Annotation*,Signature,InnerClasses,EnclosingMethod
-keepclassmembers class * {
    @kotlinx.serialization.Serializable *;
}

# Preserve Security Keystore wrappers
-keep class org.ares.agent.security.** { *; }
-keep class org.ares.agent.domain.model.** { *; }
-keep class org.ares.agent.protocol.** { *; }
