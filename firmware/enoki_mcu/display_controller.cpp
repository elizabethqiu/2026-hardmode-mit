#include "display_controller.h"
#include <st7789v2.h>
#include <SPI.h>

static st7789v2 lcd;

// Layout regions (portrait 240x280):
//   y=0..149   : face area
//   y=150..199 : state bar
//   y=200..259 : message area
//   y=260..279 : grove dots

static const uint16_t FACE_Y      = 0;
static const uint16_t FACE_H      = 150;
static const uint16_t STATE_Y     = 150;
static const uint16_t STATE_H     = 50;
static const uint16_t MSG_Y       = 200;
static const uint16_t MSG_H       = 60;
static const uint16_t GROVE_Y     = 260;
static const uint16_t GROVE_H     = 20;

static const uint16_t COL_BG      = 0x0000;  // black
static const uint16_t COL_GREEN   = 0x07E0;
static const uint16_t COL_AMBER   = 0xFD20;
static const uint16_t COL_RED     = 0xF800;
static const uint16_t COL_WARM    = 0xCE59;
static const uint16_t COL_WHITE   = 0xFFFF;
static const uint16_t COL_GRAY    = 0x8410;

void DisplayController::begin() {
  lcd.Init(DISP_CS, DISP_DC, DISP_RST, DISP_BL);
  lcd.SetRotate(0);  // portrait
  lcd.SetBacklight(200);
  lcd.Clear(COL_BG);

  memset(current_mood_, 0, sizeof(current_mood_));
  memset(current_msg_, 0, sizeof(current_msg_));
  strncpy(current_mood_, "watchful", sizeof(current_mood_) - 1);
}

uint16_t DisplayController::moodToColor(const char* mood) {
  if (strcmp(mood, "focused") == 0)   return COL_GREEN;
  if (strcmp(mood, "watchful") == 0)  return COL_WARM;
  if (strcmp(mood, "concerned") == 0) return COL_AMBER;
  if (strcmp(mood, "gentle") == 0)    return COL_AMBER;
  if (strcmp(mood, "urgent") == 0)    return COL_RED;
  return COL_WARM;
}

void DisplayController::clearRegion(uint16_t y, uint16_t h, uint16_t color) {
  lcd.ClearWindow(0, y, SCREEN_W - 1, y + h - 1, color);
}

void DisplayController::drawFace(const char* mood, uint16_t color) {
  clearRegion(FACE_Y, FACE_H, COL_BG);

  // Center of face area
  int cx = SCREEN_W / 2;   // 120
  int cy = FACE_Y + 65;    // vertical center of face region

  if (strcmp(mood, "focused") == 0) {
    // Wide open eyes, smile
    lcd.DrawCircle(cx - 35, cy - 10, 14, color, DOT_PIXEL_2X2, DRAW_FILL_FULL);
    lcd.DrawCircle(cx + 35, cy - 10, 14, color, DOT_PIXEL_2X2, DRAW_FILL_FULL);
    // Pupils
    lcd.DrawCircle(cx - 35, cy - 10, 5, COL_BG, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    lcd.DrawCircle(cx + 35, cy - 10, 5, COL_BG, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    // Smile arc (approximate with lines)
    lcd.DrawLine(cx - 25, cy + 25, cx, cy + 35, color, DOT_PIXEL_2X2, LINE_STYLE_SOLID);
    lcd.DrawLine(cx, cy + 35, cx + 25, cy + 25, color, DOT_PIXEL_2X2, LINE_STYLE_SOLID);
  }
  else if (strcmp(mood, "watchful") == 0) {
    // Normal eyes, neutral mouth
    lcd.DrawCircle(cx - 35, cy - 10, 12, color, DOT_PIXEL_2X2, DRAW_FILL_FULL);
    lcd.DrawCircle(cx + 35, cy - 10, 12, color, DOT_PIXEL_2X2, DRAW_FILL_FULL);
    lcd.DrawCircle(cx - 35, cy - 10, 4, COL_BG, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    lcd.DrawCircle(cx + 35, cy - 10, 4, COL_BG, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    // Straight mouth
    lcd.DrawLine(cx - 18, cy + 28, cx + 18, cy + 28, color, DOT_PIXEL_2X2, LINE_STYLE_SOLID);
  }
  else if (strcmp(mood, "concerned") == 0) {
    // Squinting eyes (half circles), slight frown
    lcd.DrawLine(cx - 48, cy - 10, cx - 22, cy - 10, color, DOT_PIXEL_3X3, LINE_STYLE_SOLID);
    lcd.DrawLine(cx + 22, cy - 10, cx + 48, cy - 10, color, DOT_PIXEL_3X3, LINE_STYLE_SOLID);
    // Small pupils below the line
    lcd.DrawCircle(cx - 35, cy - 4, 3, color, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    lcd.DrawCircle(cx + 35, cy - 4, 3, color, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    // Frown
    lcd.DrawLine(cx - 20, cy + 32, cx, cy + 26, color, DOT_PIXEL_2X2, LINE_STYLE_SOLID);
    lcd.DrawLine(cx, cy + 26, cx + 20, cy + 32, color, DOT_PIXEL_2X2, LINE_STYLE_SOLID);
  }
  else if (strcmp(mood, "gentle") == 0) {
    // Soft closed eyes (arcs), small mouth
    lcd.DrawLine(cx - 48, cy - 6, cx - 35, cy - 14, color, DOT_PIXEL_2X2, LINE_STYLE_SOLID);
    lcd.DrawLine(cx - 35, cy - 14, cx - 22, cy - 6, color, DOT_PIXEL_2X2, LINE_STYLE_SOLID);
    lcd.DrawLine(cx + 22, cy - 6, cx + 35, cy - 14, color, DOT_PIXEL_2X2, LINE_STYLE_SOLID);
    lcd.DrawLine(cx + 35, cy - 14, cx + 48, cy - 6, color, DOT_PIXEL_2X2, LINE_STYLE_SOLID);
    // Small 'o' mouth
    lcd.DrawCircle(cx, cy + 28, 6, color, DOT_PIXEL_2X2, DRAW_FILL_EMPTY);
  }
  else if (strcmp(mood, "urgent") == 0) {
    // Wide eyes with exclamation, open mouth
    lcd.DrawCircle(cx - 35, cy - 10, 16, color, DOT_PIXEL_2X2, DRAW_FILL_FULL);
    lcd.DrawCircle(cx + 35, cy - 10, 16, color, DOT_PIXEL_2X2, DRAW_FILL_FULL);
    lcd.DrawCircle(cx - 35, cy - 10, 6, COL_BG, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    lcd.DrawCircle(cx + 35, cy - 10, 6, COL_BG, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    // Open mouth (oval)
    lcd.DrawCircle(cx, cy + 30, 10, color, DOT_PIXEL_2X2, DRAW_FILL_EMPTY);
  }
  else {
    // Fallback: watchful
    lcd.DrawCircle(cx - 35, cy - 10, 12, COL_WARM, DOT_PIXEL_2X2, DRAW_FILL_FULL);
    lcd.DrawCircle(cx + 35, cy - 10, 12, COL_WARM, DOT_PIXEL_2X2, DRAW_FILL_FULL);
    lcd.DrawLine(cx - 18, cy + 28, cx + 18, cy + 28, COL_WARM, DOT_PIXEL_2X2, LINE_STYLE_SOLID);
  }
}

void DisplayController::showMood(const char* mood) {
  if (strcmp(mood, current_mood_) == 0) return;  // no change
  strncpy(current_mood_, mood, sizeof(current_mood_) - 1);
  current_mood_[sizeof(current_mood_) - 1] = '\0';

  uint16_t color = moodToColor(mood);
  drawFace(mood, color);
}

void DisplayController::showMessage(const char* msg) {
  if (!msg || strlen(msg) == 0) return;
  if (strcmp(msg, current_msg_) == 0) return;  // no change
  strncpy(current_msg_, msg, sizeof(current_msg_) - 1);
  current_msg_[sizeof(current_msg_) - 1] = '\0';

  clearRegion(MSG_Y, MSG_H, COL_BG);

  // Word-wrap: ~26 chars per line at Font12, 3 lines fit in 60px
  const int LINE_CHARS = 26;
  const int LINE_HEIGHT = 16;
  int len = strlen(msg);
  int y = MSG_Y + 4;
  int pos = 0;

  for (int line = 0; line < 3 && pos < len; line++) {
    int end = pos + LINE_CHARS;
    if (end >= len) {
      end = len;
    } else {
      // Find last space before cutoff for word wrap
      int last_space = end;
      while (last_space > pos && msg[last_space] != ' ') last_space--;
      if (last_space > pos) end = last_space;
    }

    char buf[LINE_CHARS + 1];
    int n = end - pos;
    memcpy(buf, msg + pos, n);
    buf[n] = '\0';

    lcd.DrawString_EN(8, y, buf, &Font12, COL_BG, COL_WHITE);
    y += LINE_HEIGHT;
    pos = end;
    if (pos < len && msg[pos] == ' ') pos++;  // skip space at wrap point
  }
}

void DisplayController::showState(const char* state, int focusMinutes) {
  clearRegion(STATE_Y, STATE_H, COL_BG);

  // State label on left
  lcd.DrawString_EN(8, STATE_Y + 8, state, &Font20, COL_BG, COL_WHITE);

  // Timer on right
  char timer[16];
  snprintf(timer, sizeof(timer), "%dm", focusMinutes);
  lcd.DrawString_EN(SCREEN_W - 60, STATE_Y + 8, timer, &Font20, COL_BG, COL_GREEN);

  // Separator line
  lcd.DrawLine(0, STATE_Y + STATE_H - 2, SCREEN_W - 1, STATE_Y + STATE_H - 2,
               COL_GRAY, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
}

void DisplayController::showGroveStatus(const int colors[][3], int count) {
  clearRegion(GROVE_Y, GROVE_H, COL_BG);
  if (count <= 0) return;

  int dotR = 6;
  int spacing = 20;
  int totalW = count * spacing;
  int startX = (SCREEN_W - totalW) / 2 + dotR;
  int cy = GROVE_Y + GROVE_H / 2;

  for (int i = 0; i < count && i < MAX_GROVE; i++) {
    uint16_t c = ((colors[i][0] & 0xF8) << 8) |
                 ((colors[i][1] & 0xFC) << 3) |
                 ((colors[i][2] >> 3));
    lcd.DrawCircle(startX + i * spacing, cy, dotR, c, DOT_PIXEL_1X1, DRAW_FILL_FULL);
  }
}

void DisplayController::setBacklight(uint8_t value) {
  lcd.SetBacklight(value);
}

void DisplayController::clear() {
  lcd.Clear(COL_BG);
}
