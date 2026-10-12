/* Archimedes Elite (Hybrid Technology, 1991; Warren Burch and Clive
 * Gringras), version 1.14 as patched by Jeffrey Lee: what libroger needs
 * to know about the game.
 *
 * !Run: Set Elite$Dir <Obey$Dir> ; Set EliteSounds$Dir <Elite$Dir>.Sounds ;
 * WimpSlot 450K ; RMEnsure SharedCLibrary 3.76 RMLoad System:Modules.Clib ;
 * RMEnsure CLockUtils 0.00 RMLoad <Elite$Dir>.CLockUtils ; Run
 * <Elite$Dir>.elite %*0. The program is C on the Shared C Library (which
 * libroger provides), a Wimp front end that starts the full-screen game.
 * CLockUtils turns a joystick into key presses: there is none, so it isn't
 * loaded. The sound modules are RMLoaded by the game (Sounds.LoadSounds). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <roger.h>

extern const struct roger_image recomp_image;      /* gen/elite/entries.c */
#include "gen/modules.inc"                         /* the sound modules */

static const char *const prefixes[] = {"<Obey$Dir>.", NULL};
static const char *const variables[] = {
    "Elite$Dir", "!Elite", "EliteSounds$Dir", "!Elite.Sounds", "System$Path", "!System.",
    "File$Type_C87", "EliteCom", NULL,
};

/* What !Boot does when the Filer first sees the application; and on the
 * desktop (--desktop), the commanders' directory open, to load one from
 * (double-click, or drag it to the icon bar icon) and save to (drag the
 * save box's icon there) */
static void game_init(void)
{
    roger_cli("IconSprites <Elite$Dir>.!Sprites");
    roger_filer_open("Commanders");
}

/* ---- The front end, without a desktop to show it on.
 *
 * Its icon bar menu is Info, Preferences, Commander, Save, Quit;
 * Preferences and Save open dialogue boxes (the templates "preferences" and
 * "xfer_send"). game.c stands in for the user (wimp_idle: Wimp_Poll has
 * nothing else to do):
 * - at the start, with --mouse= &c., Preferences: set its icons, then Save
 *   (the front end writes its Choices - to the save directory);
 * - Select on the icon bar icon starts (or resumes) the game;
 * - each time the game returns to the desktop (its DESK key or bar), Save:
 *   the commander is saved as Commanders.<name> (the save box's name, put
 *   in a directory: a name with a "." is saved there directly) - in the
 *   save directory, from where --commander=Commanders.<name> loads it -
 *   then the game resumes.
 * A commander file to start with (--commander=) is passed on the command
 * line, as double-clicking one does. */
static char command_line[1100] = "!Elite.Elite";

/* preferences: -1 leave as the Choices file has it */
static int pref_mouse = -1, pref_right = -1, pref_tune = -1, pref_sens = -1;

enum { PREFS_MENU, PREFS_SET, START, PLAYING, SAVE_SELECT, SAVE_FILL, RESUME };
static int state = PREFS_MENU;

static uint32_t sys_regs[10];
static void wimp_swi(uint32_t n)          /* (registers as set in sys_regs) */
{
    for (int k = 0; k < 10; k++) R[k] = sys_regs[k];
    roger_swi(n | 0x20000);
}

/* an option icon on or off: clicked, as the user would, if it isn't
 * already (the front end keeps the setting as the clicks change it) */
static void set_selected(int32_t w, int icon, int on)
{
    uint32_t b = roger_scratch("");
    WR32(b, (uint32_t)w); WR32(b + 4, (uint32_t)icon);
    sys_regs[1] = b;
    wimp_swi(0x400CE);                    /* Wimp_GetIconState: the icon at +8, its flags at +24 */
    if (!VF && ((RD32(b + 24) >> 21) & 1) != (uint32_t)on) roger_wimp_click(w, icon, 4);
}

static void set_text(uint32_t buf, const char *t)
{
    size_t l = strlen(t);
    memcpy(MEM + buf, t, l);
    MEM[buf + l] = 13;
}

static void wimp_idle(void)
{
    static const int prefs_item[] = {1, -1}, save_item[] = {3, -1};
    int32_t w;
    switch (state) {
    case PREFS_MENU:
        if (pref_mouse < 0 && pref_right < 0 && pref_tune < 0 && pref_sens < 0) { state = START; wimp_idle(); return; }
        roger_wimp_click(-2, 0, 2);                         /* Menu on the icon */
        roger_wimp_menu(prefs_item);
        state = PREFS_SET;
        return;
    case PREFS_SET:
        if ((w = roger_wimp_menu_window())) {
            if (pref_mouse >= 0) set_selected(w, 1, pref_mouse);
            if (pref_right >= 0) set_selected(w, 2, pref_right);
            if (pref_tune >= 0) set_selected(w, 6, pref_tune);
            if (pref_sens >= 0) {
                char t[4]; snprintf(t, sizeof t, "%d", pref_sens);
                uint32_t b = roger_wimp_icon_buffer(w, 5);
                if (b) set_text(b, t);
            }
            roger_wimp_click(w, 10, 4);                     /* Save */
            roger_wimp_click(w, 0, 4);                      /* OK */
        } else fprintf(stderr, "elite: the Preferences box didn't open\n");
        state = START;
        return;
    case START: case RESUME:
        roger_wimp_click(-2, 0, 4);                         /* Select on the icon: play */
        state = PLAYING;
        return;
    case PLAYING:                                           /* back at the desktop: save */
        roger_wimp_click(-2, 0, 2);
        roger_wimp_menu(save_item);
        state = SAVE_FILL;
        return;
    case SAVE_FILL:
        if ((w = roger_wimp_menu_window())) {
            uint32_t b = roger_wimp_icon_buffer(w, 2);
            char name[256] = "", to[300];
            for (int k = 0; b && k < 255 && MEM[b + k] >= 32; k++) name[k] = MEM[b + k], name[k + 1] = 0;
            snprintf(to, sizeof to, strchr(name, '.') ? "%s" : "Commanders.%s", *name ? name : "Commander");
            if (b) set_text(b, to);
            fprintf(stderr, "elite: saving the commander as %s\n", to);
            roger_wimp_save_to(to);                         /* (the front end saves by drag: to a Filer) */
            roger_wimp_click(w, 0, 4);                      /* OK */
        } else fprintf(stderr, "elite: the save box didn't open\n");
        state = RESUME;
        return;
    }
}

static int onoff(const char *v) { return !strcmp(v, "on") || !strcmp(v, "1") || !strcmp(v, "yes"); }

static int game_arg(const char *a)
{
    if (!strncmp(a, "--commander=", 12)) {
        const char *f = a + 12;
        char host[2048];
        /* a host file, or a RISC OS name (e.g. Commanders.Jameson) */
        if (strchr(f, '/') && realpath(f, host)) snprintf(command_line, sizeof command_line, "!Elite.Elite HostFS:%s", host);
        else snprintf(command_line, sizeof command_line, "!Elite.Elite %s", f);
        return 1;
    }
    if (!strncmp(a, "--mouse=", 8)) { pref_mouse = onoff(a + 8); return 1; }
    if (!strncmp(a, "--right-handed=", 15)) { pref_right = onoff(a + 15); return 1; }
    if (!strncmp(a, "--tune=", 7)) { pref_tune = onoff(a + 7); return 1; }
    if (!strncmp(a, "--sensitivity=", 14)) { pref_sens = atoi(a + 14); if (pref_sens < 1) pref_sens = 1; if (pref_sens > 9) pref_sens = 9; return 1; }
    return 0;
}

static struct roger_config config = {
    .title = "Elite (recompiled)",
    /* a controller, for flying by keyboard (--mouse=off): roll < > (the
     * comma and full stop keys: inkey103, inkey104), dive S pushing, climb X
     * pulling, A laser, B missile (M), X target (T), Y ECM (E), the right
     * trigger faster (Space), the left slower (? /), LB hyperspace (H), RB
     * jump (J), start launch (F1); back nothing (Escape is the escape pod) */
    .pad_map = "left=inkey103,right=inkey104,up=S,down=X,a=A,b=M,x=T,y=E,rt=Space,lt=/,lb=H,rb=J,start=F1,back=none",
    .image_path = "../game/!Elite/Elite,ff8",
    .image = &recomp_image,
    .modules = modules,
    .appdir = "../game",
    .dir_prefixes = prefixes,
    .variables = variables,
    .command_line = command_line,
    .initial_mode = 12,                 /* a desktop mode */
    /* !Run's WimpSlot is 450K; libroger's Shared C Library keeps a 64K root
     * stack (no stack extension) above the image, which needs more */
    .wimpslot = 640 * 1024,
    .init = game_init,
    .wimp_idle = wimp_idle,
    .arg = game_arg,
    .usage = "  --commander=FILE  start with this commander (a RISC OS name, e.g. Commanders.Jameson,\n"
             "                    or a host file); returning to the desktop (DESK) saves it\n"
             "  --mouse=on|off --right-handed=on|off --tune=on|off --sensitivity=1-9\n"
             "                    set (and save) the front end's Preferences: --mouse=off flies by keyboard\n",
    .relative_mouse = 1,                /* flying by mouse: the game re-centres the pointer */
    .ctrl_meta_keys = 1,                /* the game uses F10-F12 */
};

int main(int argc, char **argv) { roger_main(argc, argv, &config); }
