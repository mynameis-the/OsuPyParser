# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import math
import os
from typing import List
from typing import Dict
from typing import Union
from typing import Optional
from .objects import Position
from .objects import Circle
from .objects import Slider
from .objects import Spinner
from .objects import HitObject
from .objects import Additions
from .objects import Edge
from .objects import TimingPoint
from .constants import ObjectType
from .constants import OSU_FILE_HEADER
from .constants import CURVE_TYPES


def osu_float(f):  # osu doesn't keep decimal 0s
    f = str(f)
    if f[-1:-3:-1] == "0.":
        return f[0:-2]
    return f


class OsuFile:
    """A class representing all data from .osu file.
    https://osu.ppy.sh/wiki/en/Client/File_formats/Osu_%28file_format%29
    """

    def __init__(self, file_path: str):
        self.__file_path: str = file_path

        # Header of file.
        self.file_version: int = 0

        # General section.
        self.audio_filename: str = ""
        self.audio_lead_in: int = 0
        self.preview_time: int = 0
        self.countdown: int = 0
        self.sample_set: str = ""
        self.stack_leniency: float = 0.0
        self.mode: int = 0
        self.letterbox_in_breaks: bool = False
        self.widescreen_storyboard: bool = False

        # Editor section.
        self.distance_spacing: float = 0.0
        self.beat_divisor: int = 0
        self.grid_size: int = 0
        self.timeline_zoom: float = 0.0

        # Metadata section.
        self.title: str = ""
        self.title_unicode: str = ""
        self.artist: str = ""
        self.artist_unicode: str = ""
        self.creator: str = ""
        self.version: str = ""
        self.source: str = ""
        self.tags: str = ""
        self.beatmap_id: int = 0
        self.beatmap_set_id: int = 0

        # Difficulty section.
        self.hp: float = 0.0
        self.cs: float = 0.0
        self.od: float = 0.0
        self.ar: float = 0.0
        self.slider_multiplier: float = 0.0
        self.slider_tick_rate: int = 0

        # Events section.
        self.has_video: bool = False
        self.video_file: str = ""
        self.background_file: str = ""
        self.break_times: List[List[int, int]] = []
        self.break_time: int = 0
        self.storyboards: list = []

        # TimingPoints section.
        self.timing_points: List[TimingPoint] = []

        # Colours section.
        self.colours: Dict[str, tuple] = {}

        # HitObjects section.
        self.hit_objects: List[Union[HitObject, Circle, Slider, Spinner]] = []

        # External data.
        self.md5: str = ""
        self.max_combo: int = 0
        self.bpm: int = -1
        self.total_hits: int = 0
        self.play_time: float = 0.0
        self.drain_time: float = 0.0
        self.ncircles: int = 0
        self.nsliders: int = 0
        self.nspinners: int = 0

    def save_file(self, path):
        """Saves parsed beatmap to .osu file"""
        with open(path, "r") as f:
            f.write(self.unparse_file())

    def parse_file(self):
        """Parses sections and set them to class variables."""

        with open(self.__file_path, "rb") as stream:
            buffer = stream.read()
        # Strip lines.
        lines = list(
            map(lambda x: x.strip(), buffer.decode("utf-8-sig").split("\n")))
        self.md5 = hashlib.md5(buffer).digest().hex()

        header_line = lines[0]
        if header_line[:len(OSU_FILE_HEADER)] != OSU_FILE_HEADER:
            # First line should have osu special header.
            raise ValueError(
                f"Unknown file error! Excepted: {OSU_FILE_HEADER}, got {header_line}")
        self.file_version = int(header_line[len(OSU_FILE_HEADER):])

        section_name = ""
        for line in lines[1:]:
            if not line:
                continue  # Just continue looping.

            if line[0] == "[" and line[-1] == "]":
                section_name = line[1:-1].lower()
                continue

            # Call parser to take care of it.
            section_parser = getattr(self, f"{section_name}_parser", None)
            if not section_parser:
                continue
            section_parser(line)

        self.calculate_minor_things()
        self.calculate_max_combo()
        # Return self as some people would want to make one line parsing.
        return self

    def unparse_file(self):
        newline = "\n"
        data = f"""osu file format v14

[General]
{self.unparse_general()}

[Editor]
{self.unparse_editor()}

[Metadata]
{self.unparse_metadata()}

[Difficulty]
{self.unparse_difficulty()}

[Events]
{self.unparse_events()}

[TimingPoints]
{self.unparse_timingpoints()}

[Colours]
{self.unparse_colours()}

[HitObjects]
{self.unparse_hit_objects()}
"""
        return data

    def general_parser(self, line: str) -> None:
        """Parses [General] header data."""
        if line.startswith("AudioFilename"):
            self.audio_filename = line.split("AudioFilename:")[1].strip()
        elif line.startswith("AudioLeadIn"):
            self.audio_lead_in = int(line.split("AudioLeadIn:")[1].strip())
        elif line.startswith("PreviewTime"):
            self.preview_time = int(line.split("PreviewTime:")[1].strip())
        elif line.startswith("Countdown"):
            self.countdown = int(line.split("Countdown:")[1].strip())
        elif line.startswith("SampleSet"):
            self.sample_set = line.split("SampleSet:")[1].strip()
        elif line.startswith("StackLeniency"):
            self.stack_leniency = float(
                line.split("StackLeniency:")[1].strip())
        elif line.startswith("Mode"):
            self.mode = int(line.split("Mode:")[1].strip())
        elif line.startswith("LetterboxInBreaks"):  # Making it bool.
            self.letterbox_in_breaks = "1" == line.split(
                "LetterboxInBreaks:")[1].strip()
        elif line.startswith("WidescreenStoryboard"):  # Same here.
            self.widescreen_storyboard = "1" == line.split(
                "WidescreenStoryboard:")[1].strip()

    def unparse_general(self):
        return f"""AudioFilename: {self.audio_filename}
AudioLeadIn: {self.audio_lead_in}
PreviewTime: {self.preview_time}
Countdown: {self.countdown}
SampleSet: {self.sample_set}
StackLeniency: {self.stack_leniency}
Mode: {self.mode}
LetterboxInBreaks: {int(self.letterbox_in_breaks)}
WidescreenStoryboard: {int(self.widescreen_storyboard)}"""

    def editor_parser(self, line: str) -> None:
        """Parses [Editor] header data."""
        if line.startswith("DistanceSpacing"):
            self.distance_spacing = float(
                line.split("DistanceSpacing:")[1].strip())
        elif line.startswith("BeatDivisor"):
            self.beat_divisor = int(line.split("BeatDivisor:")[1].strip())
        elif line.startswith("GridSize"):
            self.grid_size = int(line.split("GridSize:")[1].strip())
        elif line.startswith("TimelineZoom"):
            self.timeline_zoom = float(line.split("TimelineZoom:")[1].strip())

    def unparse_editor(self):
        return f"""DistanceSpacing: {self.distance_spacing}
BeatDivisor: {self.beat_divisor}
GridSize: {self.grid_size}
TimelineZoom: {self.timeline_zoom}"""

    def metadata_parser(self, line: str) -> None:
        """Parses [Metadata] header data."""
        if line.startswith("Title:"):
            self.title = line.split("Title:")[1].strip()
        elif line.startswith("TitleUnicode"):
            self.title_unicode = line.split("TitleUnicode:")[1].strip()
        elif line.startswith("Artist:"):
            self.artist = line.split("Artist:")[1].strip()
        elif line.startswith("ArtistUnicode"):
            self.artist_unicode = line.split("ArtistUnicode:")[1].strip()
        elif line.startswith("Creator"):
            self.creator = line.split("Creator:")[1].strip()
        elif line.startswith("Version"):
            self.version = line.split("Version:")[1].strip()
        elif line.startswith("Source"):
            self.source = line.split("Source:")[1].strip()
        elif line.startswith("Tags"):
            self.tags = line.split("Tags:")[1].strip()
        elif line.startswith("BeatmapID"):
            self.beatmap_id = int(line.split("BeatmapID:")[1].strip())
        elif line.startswith("BeatmapSetID"):
            self.beatmap_set_id = int(line.split("BeatmapSetID:")[1].strip())

    def unparse_metadata(self):
        return f"""Title:{self.title}
TitleUnicode:{self.title_unicode}
Artist:{self.artist}
ArtistUnicode:{self.artist_unicode}
Creator:{self.creator}
Version:{self.version}
Source:{self.source}
Tags: {self.tags}
BeatmapID:{self.beatmap_id}
BeatmapSetID:{self.beatmap_set_id}"""

    def difficulty_parser(self, line: str) -> None:
        """Parses [Difficulty] header data."""
        if line.startswith("HPDrainRate"):
            self.hp = float(line.split("HPDrainRate:")[1].strip())
        elif line.startswith("CircleSize"):
            self.cs = float(line.split("CircleSize:")[1].strip())
        elif line.startswith("OverallDifficulty"):
            self.od = float(line.split("OverallDifficulty:")[1].strip())
        elif line.startswith("ApproachRate"):
            self.ar = float(line.split("ApproachRate:")[1].strip())
        elif line.startswith("SliderMultiplier"):
            self.slider_multiplier = float(
                line.split("SliderMultiplier:")[1].strip())
        elif line.startswith("SliderTickRate"):
            self.slider_tick_rate = float(
                line.split("SliderTickRate:")[1].strip())

    def unparse_difficulty(self):
        return f"""HPDrainRate:{osu_float(self.hp)}
CircleSize:{osu_float(self.cs)}
OverallDifficulty:{osu_float(self.od)}
ApproachRate:{osu_float(self.ar)}
SliderMultiplier:{osu_float(self.slider_multiplier)}
SliderTickRate:{osu_float(self.slider_tick_rate)}"""

    def events_parser(self, line: str) -> None:
        """Parses [Events] header data."""
        if not line.startswith("//"):
            data = line.split(",")

            if data and data[0] == "Video":
                self.has_video = True
                self.video_file = data[2]
                if data[2][0] == '"':
                    self.video_file = data[2][1:-1]

            elif data and data[0] == "0" and data[1] == "0":
                # Its most likely background.
                self.background_file = data[2]
                if data[2][0] == '"':  # Fix it then.
                    self.background_file = data[2][1:-1]

            elif data and data[0] == "2":
                self.break_times.append([int(data[1]), int(data[2])])

    def unparse_events(self):
        newline = "\n"
        return f"""//Background and Video events
0,0,"{self.background_file}",0,0
//Break Periods
{newline.join([",".join(map(str, [2]+i)) for i in self.break_times])}
//Storyboard Layer 0 (Background)
//Storyboard Layer 1 (Fail)
//Storyboard Layer 2 (Pass)
//Storyboard Layer 3 (Foreground)
//Storyboard Layer 4 (Overlay)
//Storyboard Sound Samples"""

    # Taken from https://github.com/nojhamster/osu-parser/blob/539b73e087d46de7aa7159476c7ea6ac50983c97/index.js#L99
    def timingpoints_parser(self, line: str) -> None:
        """Parses [TimingPoints] header data."""
        data = line.split(",")
        point = TimingPoint(
            offset=float(data[0]),
            beat_length=float(data[1]),
            velocity=1,
            time_signature=int(data[2]),
            sample_set_id=int(data[3]),
            custom_sample_index=int(data[4]),
            sample_volume=int(data[5]),
            timing_change=None if not len(data) > 6 else '1' == data[6],
            kiai_time_active=None if not len(data) > 7 else '1' == data[7]
        )

        if point.beat_length:
            if len(self.timing_points) == 0:
                # Only first index contains bpm data.
                self.bpm = point.bpm = round(60000 / point.beat_length)
            else:
                # If negative, beat_length is a velocity factor.
                point.velocity = abs(100 / point.beat_length)

        self.timing_points.append(point)

    def unparse_timingpoints(self):
        lines = []
        for timingpoint in self.timing_points:
            attributes = [
                osu_float(timingpoint.offset),
                osu_float(timingpoint.beat_length),
                osu_float(timingpoint.time_signature),
                osu_float(timingpoint.sample_set_id),
                osu_float(timingpoint.custom_sample_index),
                osu_float(timingpoint.sample_volume),
            ]
            if timingpoint.timing_change is not None:
                attributes.append(str(int(timingpoint.timing_change)))
            if timingpoint.kiai_time_active is not None:
                attributes.append(str(int(timingpoint.kiai_time_active)))
            lines.append(",".join(attributes))
        return "\n".join(lines)

    def colours_parser(self, line: str) -> None:
        """Parses [Colours] header data."""
        name, rgb_colours = line.split(" : ")
        rgb = rgb_colours.split(",")

        self.colours |= {name: (int(rgb[0]), int(rgb[1]), int(rgb[2]))}

    def unparse_colours(self):
        return "\n".join([f"k : {','.join(map(str, v))}" for k, v in self.colours.items()]) if self.colours else ""

    # Also taken from https://github.com/nojhamster/osu-parser/blob/539b73e087d46de7aa7159476c7ea6ac50983c97/index.js#L134
    def hitobjects_parser(self, line: str) -> None:
        """Parses [HitObjects] header data."""
        data = line.split(",")

        _type = int(data[3])
        sound = int(data[4])
        new_combo = (_type & ObjectType.NEW_COMBO) == 4
        pos = Position(int(data[0]), int(data[1]))
        colour_hax = (_type & int("01110000", base=2)) >> 4

        if _type & ObjectType.CIRCLE:
            self.ncircles += 1
            hitobject = Circle(
                pos=pos,
                start_time=int(data[2]),
                new_combo=new_combo,
                colour_hax=colour_hax,
                sound_enum=sound
            )
            if len(data) > 5:
                hitobject.additions = self.parse_addition(data[5])
        elif _type & ObjectType.SPINNER:
            self.nspinners += 1
            hitobject = Spinner(
                pos=pos,
                start_time=int(data[2]),
                new_combo=new_combo,
                colour_hax=colour_hax,
                sound_enum=sound,
                end_time=int(data[5])
            )
            if len(data) > 6:
                hitobject.additions = self.parse_addition(data[6])
        elif _type & ObjectType.SLIDER:
            self.nsliders += 1
            duration = 0
            curve_type = ""
            points_list = []
            edges = []

            timing = self.get_timing_point(int(data[2]))
            if timing:
                px_per_beat = self.slider_multiplier * 100 * timing.velocity
                beats_count = (float(data[7]) * int(data[6])) / px_per_beat
                duration = math.ceil(beats_count * timing.beat_length)

            points = ('' if not len(data) > 5 else data[5]).split("|")
            if points:
                curve_type = CURVE_TYPES.get(points[0])
                for point in points[1:]:
                    x, y = point.split(":")
                    points_list.append(Position(int(x), int(y)))

            edge_sounds = ('' if not len(data) > 8 else data[8]).split("|")
            edge_additions = ('' if not len(data) > 9 else data[9]).split("|")

            for i in range(0, int(data[6]) + 1):
                additions = None
                sound_edge_enum = None
                if i < len(edge_additions):
                    additions = self.parse_addition(edge_additions[i])
                if i < len(edge_sounds):
                    sound_edge_enum = edge_sounds[i]
                edges.append(Edge(sound_edge_enum, additions))

            hitobject = Slider(
                pos=Position(int(data[0]), int(data[1])),
                start_time=int(data[2]),
                new_combo=new_combo,
                colour_hax=colour_hax,
                sound_enum=sound,
                repeat_count=int(data[6]),
                pixel_length=float(data[7]),
                edges=edges,
                points=points_list,
                duration=duration,
                end_time=(int(data[2]) + duration),
                curve_type=curve_type,
                end_position=points_list[-1]
            )
            if len(data) > 10:
                hitobject.additions = self.parse_addition(data[10])
        else:
            # Might be some hitobject I don't know about..
            hitobject = HitObject(
                pos=Position(int(data[0]), int(data[1])),
                start_time=int(data[2]),
                new_combo=new_combo,
                colour_hax=colour_hax,
                sound_enum=sound
            )

        self.total_hits += 1
        self.hit_objects.append(hitobject)

    def unparse_hit_objects(self):
        lines = []
        for hit_object in self.hit_objects:
            if type(hit_object) is Circle:
                data = [
                    str(hit_object.pos.x),
                    str(hit_object.pos.y),
                    str(hit_object.start_time),
                    str(int(ObjectType.CIRCLE) + int(hit_object.new_combo)*int(ObjectType.NEW_COMBO) + (hit_object.colour_hax << 4)),
                    str(hit_object.sound_enum),
                ]
                if hit_object.additions:
                    data.append(self.unparse_addition(hit_object))
                lines.append(",".join(data))
            elif type(hit_object) is Slider:
                data = [
                    str(hit_object.pos.x),
                    str(hit_object.pos.y),
                    str(hit_object.start_time),
                    str(int(ObjectType.SLIDER) + int(hit_object.new_combo)*int(ObjectType.NEW_COMBO) + (hit_object.colour_hax << 4)),
                    str(hit_object.sound_enum),
                    "|".join([hit_object.curve_type[0]] + [str(point.x) + ":" + str(point.y) for point in hit_object.points]),
                    str(hit_object.repeat_count),
                    osu_float(hit_object.pixel_length),
                ]
                if hit_object.edges and hit_object.edges[0].sound_types != '':
                    edge_sounds = [edge.sound_types for edge in hit_object.edges]
                    data.append("|".join(edge_sounds))
                    edge_sets = [self.unparse_edge_addition(edge) for edge in hit_object.edges]
                    data.append("|".join(edge_sets))

                if hit_object.additions:
                    data.append(self.unparse_addition(hit_object))
                lines.append(",".join(data))
            elif type(hit_object) is Spinner:
                data = [
                    str(hit_object.pos.x),
                    str(hit_object.pos.y),
                    str(hit_object.start_time),
                    str(int(ObjectType.SPINNER) + int(hit_object.new_combo)*int(ObjectType.NEW_COMBO) + (hit_object.colour_hax << 4)),
                    str(hit_object.sound_enum),
                    str(hit_object.end_time),
                ]
                if hit_object.additions:
                    data.append(self.unparse_addition(hit_object))
                lines.append(",".join(data))
        return "\n".join(lines)


    def parse_addition(self, line: str) -> Optional[Additions]:
        """Parses additional hitobject data."""
        if not line:
            return None

        samples = {
            "1": 'Normal',
            "2": "Soft",
            "3": "Drum"
        }
        data = line.split(":")
        addition = {}
        if not data:
            return None
        if len(data) > 0:
            addition['normal'] = samples.get(data[0], None)
        if len(data) > 1:
            addition['additional'] = samples.get(data[1], None)
        if len(data) > 2:
            addition['custom_sample_index'] = int(data[2])
        if len(data) > 3:
            addition['volume'] = max(0, int(data[3]))
        if len(data) > 4:
            addition['filename'] = data[4]

        additional = Additions(**addition)
        return additional

    def unparse_addition(self, hit_object: Union[Circle, Slider, Spinner]):
        samples = {
            'Normal': "1",
            "Soft": "2",
            "Drum": "3",
        }
        data = []
        try:
            data.append(samples.get(hit_object.additions.normal, "0"))
            data.append(samples.get(hit_object.additions.additional, "0"))
            data.append(str(hit_object.additions.custom_sample_index))
            data.append(str(hit_object.additions.volume))
            data.append(str(hit_object.additions.filename))
        except KeyError:
            pass
        except AttributeError:
            pass
        return ":".join(data)

    def unparse_edge_addition(self, edge):
        samples = {
            'Normal': "1",
            "Soft": "2",
            "Drum": "3",
        }
        return samples.get(edge.additions.normal, "0") + ":" + samples.get(edge.additions.additional, "0")

    def get_timing_point(self, offset: int) -> TimingPoint:
        """Finds a timing point with given offset."""
        for timing in self.timing_points:
            if timing.offset <= offset:
                return timing

        return self.timing_points[0]

    # Reference https://github.com/Francesco149/pyttanko/blob/master/pyttanko.py#L265
    def calculate_max_combo(self) -> None:
        """Calculates a combo for map."""
        combo = 0
        timings = self.timing_points
        index = -1
        px_per_beat = None
        next_offset = -float("inf")

        for hitobject in self.hit_objects:
            if not isinstance(hitobject, Slider):
                combo += 1
                continue

            while next_offset != None and hitobject.start_time >= next_offset:
                index += 1
                if len(timings) > index + 1:
                    next_offset = timings[index + 1].offset
                else:
                    next_offset = None

                timing = timings[index]
                sv_multiplier = 1.0

                if not timing.timing_change and timing.beat_length < 0:
                    sv_multiplier = (-100.0 / timing.beat_length)

                px_per_beat = self.slider_multiplier * 100.0 * sv_multiplier
                if self.file_version < 8:
                    px_per_beat /= sv_multiplier

            num_beats = (
                (hitobject.pixel_length * hitobject.repeat_count) / px_per_beat
            )

            ticks = int(
                math.ceil(
                    (num_beats - 0.1) /
                    hitobject.repeat_count * self.slider_tick_rate
                )
            )

            ticks -= 1
            ticks *= hitobject.repeat_count
            ticks += hitobject.repeat_count + 1

            combo += max(0, ticks)

        self.max_combo = combo

    def calculate_minor_things(self) -> None:
        """Calculates rest of minor things."""
        first_obj = self.hit_objects[0]
        last_obj = self.hit_objects[-1]

        for break_time in self.break_times:
            self.break_time += (break_time[1] - break_time[0])

        if first_obj and last_obj:
            self.play_time = math.floor(last_obj.start_time / 1000)
            self.drain_time = math.floor(
                (last_obj.start_time - first_obj.start_time - self.break_time) / 1000)

    def __add__(self, other: OsuFile):
        """concatenates the "other" beatmap to the end of self"""
        dir_name = f"{self.title}+{other.title}"
        map_path = os.path.join(dir_name, "map.osu")
        audio_path = os.path.join(dir_name, "audio.mp3")
        try:
            os.mkdir(dir_name)
        except FileExistsError:
            pass
        with open(os.path.join(map_path), "w") as f:
            pass
        new_beatmap = OsuFile(map_path)

        # Generate new audio
        import ffmpeg  # ffmpeg-python
        audio1_filename = os.path.join(os.path.dirname(self.__file_path), self.audio_filename)
        print(audio1_filename)
        audio2_filename = os.path.join(os.path.dirname(other.__file_path), other.audio_filename)
        print(audio2_filename)
        audio1 = ffmpeg.input(audio1_filename)
        audio2 = ffmpeg.input(audio2_filename)
        new_audio = ffmpeg.concat(audio1, audio2)

        new_audio.output(os.path.join(dir_name, 'audio.mp4'))

        print(self.audio_filename)
        audio1_length = ffmpeg.probe(audio1_filename)["format"]["duration"]

        print(f"{audio1_length=}")

        new_beatmap.timing_points = self.timing_points
        for timing_point in other.timing_points:
            timing_point.offset += audio1_length
            new_beatmap.timing_points.append()

        # Header of file.
        new_beatmap.file_version = self.file_version

        # General section.
        new_beatmap.audio_filename: str = ""
        self.audio_lead_in: int = 0
        self.preview_time: int = 0
        self.countdown: int = 0
        self.sample_set: str = ""
        self.stack_leniency: float = 0.0
        self.mode: int = 0
        self.letterbox_in_breaks: bool = False
        self.widescreen_storyboard: bool = False