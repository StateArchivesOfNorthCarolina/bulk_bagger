from mover_classes.SANCBagger import SANCBagger
import sys
import yaml
import os
import shutil
import logging
import logging.config
from io import StringIO


class AutoBagger:
    meta = {
        "Contact-Name": "Jeremy Gibson",
        "Source-Organization": "State Archives of North Carolina",
        "Internal-Sender-Identifier": "autobagger.py 0.0.4"
    }

    def __init__(self, path: str) -> None:
        super().__init__()
        self.logger_template_path = None
        self._build_basic_logger()
        self.logger = logging.getLogger("autobagger")
        self.paths = path
        self.is_single = True
        self.tobag = None       # type: StringIO
        self.moved = None       # type: StringIO
        self.review = None      # type: StringIO
        if os.path.isfile(self.paths):
            self._set_report_paths()

    def _set_report_paths(self):
        # This may only be relevant to the 2018 repository restructure
        filename = os.path.split(self.paths)[-1]
        base = "L:\\Intranet\\ar\\Digital_Services\\Inventory"
        moved = os.path.join(base, "002_TO_BE_MOVED")
        review = os.path.join(base, "003_NEEDS_REVIEW")
        self.moved = open(os.path.join(moved, filename), 'w')
        self.review = open(os.path.join(review, filename), 'w')

    def _build_basic_logger(self):
        log_dir = os.path.join(os.getcwd(), 'logs')
        self.logger_template_path = os.path.join(log_dir, 'logger_template.yml')
        f = open(self.logger_template_path, 'r')
        yml = yaml.safe_load(f)
        f.close()
        yml['handlers']['error_file_handler']['filename'] = os.path.join(log_dir, 'MoveBagger_error.log')
        yml['handlers']['info_file_handler']['filename'] = os.path.join(log_dir, 'MoveBagger_info.log')
        fh = open(os.path.join(log_dir, "MVBAGGER_config.yml"), 'w')
        yaml.dump(yml, fh)
        fh.close()
        f = open(os.path.join(log_dir, "MVBAGGER_config.yml"), 'r')
        config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)

    def bag_dir(self, path=None) -> bool:
        if path is None:
            path = self.paths
        for root, dirs, files in os.walk(path):
            for f in files:
                if f == "Thumbs.db":
                    self.logger.info("CLEANED: Thumbs.db")
                    os.remove(os.path.join(root, f))
                if str(f).startswith("~") and os.path.getsize(os.path.join(root, f)) < 13*1024:
                    self.logger.info("CLEANED: Temporary File")
                    os.remove(os.path.join(root, f))
        r = SANCBagger()
        self.logger.info("BAGGING \t{}".format(path))
        if r.create_bag(path, AutoBagger.meta):
            self.logger.info("COMPLETE \t{}".format(path))
            return True
        else:
            error = r.which_error()
            self.logger.error("FAILED \t{}\t{}".format(error[0], error[1]))
            return False

    def bulk_bag(self, b: []):
        ###
        # bulk_bag: Takes a single array the first element must be a path.  The endpoint of the path
        # should be the beginning point of a bag in place bag, or a single file that needs to be bagged by itself.
        ###
        line = ''
        bag = ''
        if os.path.exists(os.path.join(b[0], 'data')):
            line = "{}\n".format('\t'.join(b))
            self.moved.write(line)
            return
        if os.path.isfile(b[0]):
            fn = os.path.split(b[0])[-1]
            new_d_name = fn.split(".")[0]
            new_path = os.path.join(os.path.dirname(b[0]), new_d_name)
            os.mkdir(new_path)
            shutil.move(b[0], new_path)
            b[0] = new_path
            bag = new_path
            line = "{}\n".format('\t'.join(b))
        else:
            line = "{}\n".format('\t'.join(b))
            bag = b[0]

        if self.bag_dir(bag):
            self.moved.write(line)
        else:
            self.review.write(line)

    def walk_target(self):
        for line in open(self.paths, 'r').readlines()[1:]:
            s = line.strip().split("\t")
            self.bulk_bag(s)


if __name__ == "__main__":
    # Expects either a path to bag or a path to tab seperated file where the first value of each line is the
    # path to be bagged.
    # File Structure:
    ##
    target = sys.argv[1]
    if os.path.isfile(target):
        ab = AutoBagger(target)
        ab.walk_target()
    else:
        # One off bagger
        ab = AutoBagger(target)
        ab.bag_dir()