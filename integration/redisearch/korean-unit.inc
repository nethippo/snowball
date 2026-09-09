
TEST_F(TokenizerTest, testKoreanLanguage) {
  ASSERT_EQ(RSLanguage_Find("korean", 0), RS_LANG_KOREAN);
  ASSERT_EQ(RSLanguage_Find("KOREAN", 6), RS_LANG_KOREAN);
  ASSERT_EQ(RSLanguage_Find("ko", 2), RS_LANG_UNSUPPORTED);
  ASSERT_STREQ(RSLanguage_ToString(RS_LANG_KOREAN), "korean");
  ASSERT_STREQ(RSLanguage_ToSnowballStemmer(RS_LANG_KOREAN), "korean");
  Stemmer *st = NewStemmer(SnowballStemmer, RS_LANG_KOREAN);
  ASSERT_NE(st, nullptr);
  size_t len = 0;
  const char *words[] = {"학생이", "사과를", "먹었다", "공부했다", "예뻤다"};
  const char *stems[] = {"+학생", "+사과", "+먹다", "+공부하다", "+예쁘다"};
  for (size_t i = 0; i < 5; ++i) {
    const char *got = st->Stem(st->ctx, words[i], strlen(words[i]), &len);
    ASSERT_NE(got, nullptr);
    ASSERT_EQ(std::string(got, len), stems[i]);
  }
  ASSERT_EQ(st->Stem(st->ctx, "걸었다", strlen("걸었다"), &len), nullptr);
  ASSERT_EQ(st->Stem(st->ctx, "내가", strlen("내가"), &len), nullptr);
  st->Free(st);
}
