#include <jni.h>
#include <stdio.h>
#include <android/log.h>
#include <string.h>
#include <stdlib.h>

JNIEnv *SDL_ANDROID_GetJNIEnv(void);
#define aassert(x) { if (!x) { __android_log_print(ANDROID_LOG_ERROR, "android_jni", "Assertion failed. %s:%d", __FILE__, __LINE__); abort(); }}

void intent_vibrate(double seconds) {   
    static JNIEnv *env = NULL;
    static jclass *cls = NULL;
    static jmethodID mid = NULL;

    if (env == NULL) {
        env = SDL_ANDROID_GetJNIEnv();
        aassert(env);
        cls = (*env)->FindClass(env, "org/renpy/android/Hardware");
        aassert(cls);
        mid = (*env)->GetStaticMethodID(env, cls, "vibrate", "(D)V");
        aassert(mid);
    }

    (*env)->CallStaticVoidMethod(
        env, cls, mid,
        (jdouble) seconds);    
}

void intent_view(char * uri) {   
  JNIEnv *env = SDL_ANDROID_GetJNIEnv();
  aassert(env);

  // Hardware.context
  jclass *cls = (*env)->FindClass(env, "org/renpy/android/Hardware");
  aassert(cls);
  jfieldID  fid = (*env)->GetStaticFieldID(env, cls, "context", 
					   "Landroid/content/Context;");
  aassert(fid);
  jobject context = (*env)->GetStaticObjectField(env, cls, fid);
  aassert(context);

  // uri_obj = Uri.parse(uri)
  jclass *uri_cls = (*env)->FindClass(env, "android/net/Uri");
  aassert(uri_cls);
  jstring s = (*env)->NewStringUTF(env, uri);
  aassert(s);
  jmethodID uri_parse = (*env)->GetStaticMethodID(env, uri_cls, 
			    "parse", "(Ljava/lang/String;)Landroid/net/Uri;");
  aassert(uri_parse);
  jobject uri_obj = (*env)->CallStaticObjectMethod(env, uri_cls, uri_parse, s);
  aassert(uri_obj);

  // intent_obj = new Intent(Intent.ACTION_VIEW);
  jclass *intent_cls = (*env)->FindClass(env, "android/content/Intent");
  aassert(intent_cls);
  jmethodID intent_init = (*env)->GetMethodID(env, intent_cls, "<init>", 
					      "(Ljava/lang/String;)V");
  aassert(intent_init);
  jstring view = (*env)->NewStringUTF(env, "android.intent.action.VIEW");
  aassert(view);
  jobject intent_obj = (*env)->NewObject(env, intent_cls, intent_init, view);
  aassert(intent_obj);

  // intent.setData(uri_obj)
  jmethodID intent_setData = (*env)->GetMethodID(env, intent_cls, "setData", 
			      "(Landroid/net/Uri;)Landroid/content/Intent;");
  aassert(intent_setData);
  (*env)->CallObjectMethod(env, intent_obj, intent_setData, uri_obj);

  // context.startActivity(intent);
  jclass activity_cls = (*env)->FindClass(env, "android/app/Activity");
  aassert(activity_cls);
  jmethodID activity_start = (*env)->GetMethodID(env, activity_cls, 
		            "startActivity", "(Landroid/content/Intent;)V");
  aassert(activity_start);
  (*env)->CallVoidMethod(env, context, activity_start, intent_obj);

  /*
  // startActivity(intent);
  jclass activity_cls = (*env)->FindClass(env, "android/app/Activity");
  aassert(activity_cls);
  jmethodID activity_init = (*env)->GetMethodID(env, activity_cls, "<init>", 
						"()V");
  aassert(activity_init);
  jobject activity_obj = (*env)->NewObject(env, activity_cls, activity_init);
  aassert(activity_obj);
  jmethodID activity_start = (*env)->GetMethodID(env, activity_cls, 
		            "startActivity", "(Landroid/content/Intent;)V");
  aassert(activity_start);
  (*env)->CallVoidMethod(env, activity_obj, activity_start, intent_obj);
  */

}

char *intent_filename() {   
  JNIEnv *env = SDL_ANDROID_GetJNIEnv();
  aassert(env);

  // Hardware.context
  jclass *cls = (*env)->FindClass(env, "org/renpy/android/Hardware");
  aassert(cls);
  jfieldID  fid = (*env)->GetStaticFieldID(env, cls, "context", 
					   "Landroid/content/Context;");
  aassert(fid);
  jobject context = (*env)->GetStaticObjectField(env, cls, fid);
  aassert(context);

  // intent = context.getIntent();
  jclass activity_cls = (*env)->FindClass(env, "android/app/Activity");
  aassert(activity_cls);
  jmethodID get_intent = (*env)->GetMethodID(env, activity_cls, 
		            "getIntent", "()Landroid/content/Intent;");
  aassert(get_intent);
  jobject intent_obj = (*env)->CallObjectMethod(env, context, get_intent);
  aassert(intent_obj);

  // uri = intent.getData()
  jclass *intent_cls = (*env)->FindClass(env, "android/content/Intent");
  aassert(intent_cls);
  jmethodID get_data = (*env)->GetMethodID(env, intent_cls, 
		            "getData", "()Landroid/net/Uri;");
  aassert(get_data);
  jobject uri_obj = (*env)->CallObjectMethod(env, intent_obj, get_data);
  if (!uri_obj) return "";

  // uri.getPath()
  jclass *uri_cls = (*env)->FindClass(env, "android/net/Uri");
  aassert(uri_cls);
  jmethodID get_path = (*env)->GetMethodID(env, uri_cls, 
		            "getPath", "()Ljava/lang/String;");
  aassert(get_path);
  jobject path_obj = (*env)->CallObjectMethod(env, uri_obj, get_path);
  aassert(path_obj);

  return (*env)->GetStringUTFChars(env, path_obj, NULL);
}
